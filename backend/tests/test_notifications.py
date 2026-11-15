import pytest
import uuid
from datetime import date, datetime, timedelta, timezone
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.models.user import User
from app.models.project import AcademicProject, ProjectMember
from app.models.milestone import AcademicMilestone
from app.models.task import Task, TaskAssignment
from app.models.review import ProjectReview
from app.models.notification import ProjectNotification
from app.models.enums import NotificationType, TaskStatus, TaskPriority, MilestoneType, MilestoneStatus, ReviewStatus
from app.services.notification_service import NotificationService


async def register_and_login(client: AsyncClient, role: str = "student", name: str = "Test User"):
    email = f"{role}_{uuid.uuid4().hex[:8]}@college.edu"
    password = "TestPassword2026!"
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": name, "role": role},
    )
    assert reg_res.status_code == 201, reg_res.text
    user = reg_res.json()

    login_res = await client.post(
        "/api/v1/auth/login/json",
        json={"email": email, "password": password},
    )
    assert login_res.status_code == 200, login_res.text
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    return user, headers


async def create_test_project(client: AsyncClient, headers: dict, title: str = "Notification Test Project"):
    res = await client.post(
        "/api/v1/projects",
        headers=headers,
        json={
            "title": title,
            "description": "Project for testing notification functionality",
            "academic_year": "2025-2026",
            "semester": 8,
            "department": "Computer Science",
            "project_type": "capstone",
            "start_date": "2026-01-10",
            "target_deadline": "2026-05-15",
        },
    )
    assert res.status_code == 201, res.text
    return res.json()


@pytest.mark.asyncio
async def test_task_assignment_notification_creation(client: AsyncClient, db_session: AsyncSession):
    """
    Verifies that assigning a team member to a task creates a persistent in-app notification
    with task title, project title, assigner's name, due date, and link.
    """
    owner, o_headers = await register_and_login(client, role="student", name="Leader Student")
    student, s_headers = await register_and_login(client, role="student", name="Worker Student")

    project = await create_test_project(client, o_headers, title="AI Project Notification")
    project_id = project["id"]

    try:
        # Add student as project member
        add_m = await client.post(
            f"/api/v1/projects/{project_id}/members",
            headers=o_headers,
            json={"user_id": student["id"], "team_role": "developer"},
        )
        assert add_m.status_code == 201

        # Create a task
        due = (date.today() + timedelta(days=5)).isoformat()
        create_task_res = await client.post(
            f"/api/v1/projects/{project_id}/tasks",
            headers=o_headers,
            json={
                "title": "Build Neural Net Layer",
                "estimated_duration_hours": 12.0,
                "due_date": due,
                "priority": "high",
            },
        )
        assert create_task_res.status_code == 201
        task_data = create_task_res.json()
        task_id = task_data["id"]

        # Assign task to student
        assign_res = await client.post(
            f"/api/v1/tasks/{task_id}/assignments",
            headers=o_headers,
            json={"user_id": student["id"]},
        )
        assert assign_res.status_code == 201

        # Check student's notifications
        notif_res = await client.get("/api/v1/notifications", headers=s_headers)
        assert notif_res.status_code == 200
        notif_data = notif_res.json()
        assert notif_data["total_count"] >= 1
        assert notif_data["unread_count"] >= 1

        assigned_notif = next(
            (n for n in notif_data["items"] if n["task_id"] == task_id), None
        )
        assert assigned_notif is not None
        assert "Build Neural Net Layer" in assigned_notif["title"]
        assert "AI Project Notification" in assigned_notif["message"]
        assert "Leader Student" in assigned_notif["message"]
        assert assigned_notif["notification_type"] == "task_assigned"
        assert assigned_notif["link_url"] == f"/projects/{project_id}?taskId={task_id}"

        # Project owner should NOT receive the assignment notification intended for student
        owner_notif_res = await client.get("/api/v1/notifications", headers=o_headers)
        assert owner_notif_res.status_code == 200
        owner_items = owner_notif_res.json()["items"]
        assert not any(n["task_id"] == task_id and n["notification_type"] == "task_assigned" for n in owner_items)

    finally:
        await db_session.execute(delete(ProjectNotification).where(ProjectNotification.project_id == uuid.UUID(project_id)))
        await db_session.execute(delete(TaskAssignment).where(TaskAssignment.task_id == uuid.UUID(task_id)))
        await db_session.execute(delete(Task).where(Task.id == uuid.UUID(task_id)))
        await db_session.execute(delete(ProjectMember).where(ProjectMember.project_id == uuid.UUID(project_id)))
        await db_session.execute(delete(AcademicProject).where(AcademicProject.id == uuid.UUID(project_id)))
        await db_session.execute(delete(User).where(User.id.in_([uuid.UUID(owner["id"]), uuid.UUID(student["id"])])))
        await db_session.commit()


@pytest.mark.asyncio
async def test_deadline_reminders_and_overdue_alerts(client: AsyncClient, db_session: AsyncSession):
    """
    Tests 24-hour reminder, 1-hour reminder, overdue alerts, duplicate prevention,
    and exclusion of completed tasks using frozen reference times.
    """
    owner, o_headers = await register_and_login(client, role="student", name="Scheduler Lead")
    project = await create_test_project(client, o_headers, title="Deadline Test Project")
    project_id = uuid.UUID(project["id"])

    # Create 3 tasks with due date = 2026-03-10
    task_due = date(2026, 3, 10)
    # Deadline is 2026-03-10 23:59:59 UTC
    
    t_pending = Task(
        project_id=project_id,
        title="Pending Task 1",
        estimated_duration_hours=5.0,
        due_date=task_due,
        status=TaskStatus.TODO,
    )
    t_completed = Task(
        project_id=project_id,
        title="Completed Task 2",
        estimated_duration_hours=5.0,
        due_date=task_due,
        status=TaskStatus.COMPLETED,
        completed_at=datetime(2026, 3, 8, 12, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add_all([t_pending, t_completed])
    await db_session.commit()
    await db_session.refresh(t_pending)
    await db_session.refresh(t_completed)

    try:
        # 1. Reference time: 2026-03-10 08:00:00 UTC (15h 59m before deadline -> within 24h window)
        ref_24h = datetime(2026, 3, 10, 8, 0, 0, tzinfo=timezone.utc)
        stats_24h = await NotificationService.check_and_generate_deadline_reminders(
            db=db_session,
            reference_now=ref_24h,
        )
        assert stats_24h["due_in_24h_generated"] == 1
        assert stats_24h["due_in_1h_generated"] == 0
        assert stats_24h["overdue_alerts_generated"] == 0

        # Run again with same time -> duplicate prevention
        stats_repeat = await NotificationService.check_and_generate_deadline_reminders(
            db=db_session,
            reference_now=ref_24h,
        )
        assert stats_repeat["due_in_24h_generated"] == 0  # No duplicate!

        # 2. Reference time: 2026-03-10 23:15:00 UTC (44 minutes before deadline -> within 1h window)
        ref_1h = datetime(2026, 3, 10, 23, 15, 0, tzinfo=timezone.utc)
        stats_1h = await NotificationService.check_and_generate_deadline_reminders(
            db=db_session,
            reference_now=ref_1h,
        )
        assert stats_1h["due_in_1h_generated"] == 1
        assert stats_1h["due_in_24h_generated"] == 0

        # Run again -> duplicate prevention
        stats_1h_repeat = await NotificationService.check_and_generate_deadline_reminders(
            db=db_session,
            reference_now=ref_1h,
        )
        assert stats_1h_repeat["due_in_1h_generated"] == 0

        # 3. Reference time: 2026-03-11 02:00:00 UTC (past deadline -> OVERDUE)
        ref_overdue = datetime(2026, 3, 11, 2, 0, 0, tzinfo=timezone.utc)
        stats_overdue = await NotificationService.check_and_generate_deadline_reminders(
            db=db_session,
            reference_now=ref_overdue,
        )
        assert stats_overdue["overdue_alerts_generated"] == 1

        # Run again -> duplicate prevention
        stats_overdue_repeat = await NotificationService.check_and_generate_deadline_reminders(
            db=db_session,
            reference_now=ref_overdue,
        )
        assert stats_overdue_repeat["overdue_alerts_generated"] == 0

        # Verify completed task never received reminders
        notifs_q = await db_session.execute(
            select(ProjectNotification).where(
                ProjectNotification.task_id == t_completed.id
            )
        )
        assert len(list(notifs_q.scalars().all())) == 0

    finally:
        await db_session.execute(delete(ProjectNotification).where(ProjectNotification.project_id == project_id))
        await db_session.execute(delete(Task).where(Task.project_id == project_id))
        await db_session.execute(delete(ProjectMember).where(ProjectMember.project_id == project_id))
        await db_session.execute(delete(AcademicProject).where(AcademicProject.id == project_id))
        await db_session.execute(delete(User).where(User.id == uuid.UUID(owner["id"])))
        await db_session.commit()


@pytest.mark.asyncio
async def test_notification_api_endpoints_and_authorization(client: AsyncClient, db_session: AsyncSession):
    """
    Tests:
    - GET /api/v1/notifications
    - PATCH /api/v1/notifications/{id}/read
    - POST /api/v1/notifications/mark-all-read
    - Strict privacy (User cannot view or modify another user's notifications)
    - POST /api/v1/notifications/trigger-reminders
    """
    user_a, a_headers = await register_and_login(client, role="student", name="User Alpha")
    user_b, b_headers = await register_and_login(client, role="student", name="User Beta")

    user_a_id = uuid.UUID(user_a["id"])
    user_b_id = uuid.UUID(user_b["id"])

    # Create notifications directly for testing API endpoints
    n1 = await NotificationService.create_notification(
        db=db_session,
        recipient_id=user_a_id,
        title="Notice 1 for Alpha",
        message="Alpha message content",
        notification_type=NotificationType.GENERAL,
    )
    n2 = await NotificationService.create_notification(
        db=db_session,
        recipient_id=user_a_id,
        title="Notice 2 for Alpha",
        message="Alpha second message",
        notification_type=NotificationType.DUE_DATE_REMINDER,
    )
    n_beta = await NotificationService.create_notification(
        db=db_session,
        recipient_id=user_b_id,
        title="Notice for Beta",
        message="Beta message content",
        notification_type=NotificationType.TASK_ASSIGNED,
    )

    try:
        # 1. User Alpha lists notifications
        res_a = await client.get("/api/v1/notifications", headers=a_headers)
        assert res_a.status_code == 200
        data_a = res_a.json()
        assert data_a["total_count"] == 2
        assert data_a["unread_count"] == 2
        assert len(data_a["items"]) == 2
        # Verify Beta's notification is NOT visible to Alpha
        assert not any(item["id"] == str(n_beta.id) for item in data_a["items"])

        # 2. User Beta attempts to mark User Alpha's notification as read -> 404
        forbidden_patch = await client.patch(
            f"/api/v1/notifications/{n1.id}/read",
            headers=b_headers,
        )
        assert forbidden_patch.status_code == 404

        # 3. User Alpha marks n1 as read
        patch_res = await client.patch(
            f"/api/v1/notifications/{n1.id}/read",
            headers=a_headers,
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["read_at"] is not None

        # Check unread count decreased to 1
        res_a_after = await client.get("/api/v1/notifications?unread_only=true", headers=a_headers)
        assert res_a_after.status_code == 200
        assert res_a_after.json()["unread_count"] == 1
        assert len(res_a_after.json()["items"]) == 1
        assert res_a_after.json()["items"][0]["id"] == str(n2.id)

        # 4. User Alpha marks all as read
        all_read_res = await client.post("/api/v1/notifications/mark-all-read", headers=a_headers)
        assert all_read_res.status_code == 200
        assert all_read_res.json()["updated_count"] == 1

        # Check unread count is now 0
        res_a_final = await client.get("/api/v1/notifications", headers=a_headers)
        assert res_a_final.json()["unread_count"] == 0

        # 5. Trigger reminders endpoint
        trigger_res = await client.post("/api/v1/notifications/trigger-reminders", headers=a_headers)
        assert trigger_res.status_code == 200
        assert trigger_res.json()["status"] == "success"

    finally:
        await db_session.execute(delete(ProjectNotification).where(ProjectNotification.recipient_id.in_([user_a_id, user_b_id])))
        await db_session.execute(delete(User).where(User.id.in_([user_a_id, user_b_id])))
        await db_session.commit()
