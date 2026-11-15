import pytest
import uuid
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.models.user import User
from app.models.project import AcademicProject, ProjectMember
from app.models.review import ProjectReview
from app.models.notification import ProjectNotification
from app.models.enums import NotificationType, ReviewStatus


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


@pytest.mark.asyncio
async def test_faculty_review_scheduling_notifications_lifecycle(client: AsyncClient, db_session: AsyncSession):
    """
    Comprehensive test for Faculty Review Scheduling Notifications:
    1. Scheduling Review 1: alerts all enrolled students (owner + teammate), excludes outsiders.
    2. Includes project name, review type, scheduled date/time, faculty guide name, and project link.
    3. Duplicate prevention: retrying review creation does not create duplicate notifications.
    4. Rescheduling Review: changing scheduled_at sends 'Review Rescheduled' notification.
    5. Cancellation: cancelling review sends 'Review Cancelled' notification.
    6. Authorization: unauthorized faculty/students cannot schedule/modify reviews.
    7. Students can view and mark review notifications as read.
    """
    # Setup users
    faculty_supervisor, f_headers = await register_and_login(client, role="faculty", name="Dr. APJ Abdul Kalam")
    other_faculty, of_headers = await register_and_login(client, role="faculty", name="Dr. Vikram Sarabhai")
    student_owner, o_headers = await register_and_login(client, role="student", name="Aarav Lead")
    student_teammate, t_headers = await register_and_login(client, role="student", name="Ananya Dev")
    student_outsider, out_headers = await register_and_login(client, role="student", name="Rohit Outsider")

    created_users = [
        faculty_supervisor["id"],
        other_faculty["id"],
        student_owner["id"],
        student_teammate["id"],
        student_outsider["id"],
    ]

    try:
        # Create academic project supervised by faculty_supervisor
        proj_title = "Autonomous Drone Fleet Coordination"
        proj_res = await client.post(
            "/api/v1/projects",
            headers=o_headers,
            json={
                "title": proj_title,
                "description": "Multi-agent drone swarm scheduling and trajectory optimization",
                "academic_year": "2025-2026",
                "semester": 8,
                "department": "Aerospace & Computer Science",
                "project_type": "capstone",
                "start_date": "2026-01-10",
                "target_deadline": "2026-05-20",
                "faculty_guide_id": faculty_supervisor["id"],
            },
        )
        assert proj_res.status_code == 201, proj_res.text
        project_id = proj_res.json()["id"]

        # Enroll student_teammate into the project
        mem_res = await client.post(
            f"/api/v1/projects/{project_id}/members",
            headers=o_headers,
            json={"user_id": student_teammate["id"], "team_role": "developer"},
        )
        assert mem_res.status_code == 201, mem_res.text

        # =====================================================================
        # 1. SCHEDULE REVIEW 1 & VERIFY NOTIFICATIONS
        # =====================================================================
        review_time_1 = (datetime.now(timezone.utc) + timedelta(days=7)).replace(microsecond=0)
        review_time_1_str = review_time_1.isoformat()

        schedule_res = await client.post(
            f"/api/v1/faculty/projects/{project_id}/reviews",
            headers=f_headers,
            json={
                "review_number": 1,
                "scheduled_at": review_time_1_str,
                "status": "scheduled",
                "feedback": "Preliminary architecture and literature defense",
            },
        )
        assert schedule_res.status_code == 201, schedule_res.text
        review_1 = schedule_res.json()
        review_1_id = review_1["id"]

        # Verify enrolled student owner received notification
        notifs_owner_res = await client.get("/api/v1/notifications", headers=o_headers)
        assert notifs_owner_res.status_code == 200
        owner_notifs = notifs_owner_res.json()["items"]
        assert len(owner_notifs) >= 1
        owner_rev_notif = next((n for n in owner_notifs if "Review Scheduled: Review 1" in n["title"]), None)
        assert owner_rev_notif is not None
        assert proj_title in owner_rev_notif["title"]
        assert "Review 1" in owner_rev_notif["message"]
        assert "Dr. APJ Abdul Kalam" in owner_rev_notif["message"]
        assert proj_title in owner_rev_notif["message"]
        assert owner_rev_notif["link_url"] == f"/projects/{project_id}"
        assert owner_rev_notif["notification_type"] == "review_reminder"

        # Verify enrolled teammate also received notification
        notifs_team_res = await client.get("/api/v1/notifications", headers=t_headers)
        assert notifs_team_res.status_code == 200
        team_notifs = notifs_team_res.json()["items"]
        assert any("Review Scheduled: Review 1" in n["title"] for n in team_notifs)

        # Verify outsider student did NOT receive any notification
        notifs_out_res = await client.get("/api/v1/notifications", headers=out_headers)
        assert notifs_out_res.status_code == 200
        out_notifs = notifs_out_res.json()["items"]
        assert len(out_notifs) == 0

        # =====================================================================
        # 2. DUPLICATE NOTIFICATION PREVENTION ON RETRY
        # =====================================================================
        # If the backend notification trigger is called again with the same parameters
        from app.services.notification_service import NotificationService
        review_obj = await db_session.get(ProjectReview, uuid.UUID(review_1_id))
        project_obj = await db_session.get(AcademicProject, uuid.UUID(project_id))
        faculty_obj = await db_session.get(User, uuid.UUID(faculty_supervisor["id"]))

        retry_notifs = await NotificationService.notify_review_scheduled(
            db=db_session,
            review=review_obj,
            project=project_obj,
            faculty=faculty_obj,
        )
        # Should be empty because notifications already exist (idempotent duplicate prevention)
        assert len(retry_notifs) == 0

        # Check total count for owner did not increase
        notifs_owner_res2 = await client.get("/api/v1/notifications", headers=o_headers)
        assert len([n for n in notifs_owner_res2.json()["items"] if "Review Scheduled: Review 1" in n["title"]]) == 1

        # =====================================================================
        # 3. RESCHEDULING REVIEW 1
        # =====================================================================
        review_time_rescheduled = (datetime.now(timezone.utc) + timedelta(days=10)).replace(microsecond=0)
        reschedule_res = await client.put(
            f"/api/v1/faculty/projects/{project_id}/reviews/{review_1_id}",
            headers=f_headers,
            json={
                "scheduled_at": review_time_rescheduled.isoformat(),
                "feedback": "Rescheduled per academic committee availability",
            },
        )
        assert reschedule_res.status_code == 200, reschedule_res.text
        updated_rev = reschedule_res.json()
        assert updated_rev["id"] == review_1_id

        # Verify enrolled student owner received 'Review Rescheduled' notification
        notifs_owner_res3 = await client.get("/api/v1/notifications", headers=o_headers)
        owner_notifs3 = notifs_owner_res3.json()["items"]
        resched_notif = next((n for n in owner_notifs3 if "Review Rescheduled: Review 1" in n["title"]), None)
        assert resched_notif is not None
        assert "rescheduled Review 1" in resched_notif["message"]
        assert "Dr. APJ Abdul Kalam" in resched_notif["message"]

        # Verify enrolled teammate also received 'Review Rescheduled' notification
        notifs_team_res3 = await client.get("/api/v1/notifications", headers=t_headers)
        assert any("Review Rescheduled: Review 1" in n["title"] for n in notifs_team_res3.json()["items"])

        # =====================================================================
        # 4. CANCEL REVIEW 1
        # =====================================================================
        cancel_res = await client.delete(
            f"/api/v1/faculty/projects/{project_id}/reviews/{review_1_id}",
            headers=f_headers,
        )
        assert cancel_res.status_code == 200, cancel_res.text
        cancelled_rev = cancel_res.json()
        assert cancelled_rev["status"] == "cancelled"

        # Verify enrolled student owner received 'Review Cancelled' notification
        notifs_owner_res4 = await client.get("/api/v1/notifications", headers=o_headers)
        owner_notifs4 = notifs_owner_res4.json()["items"]
        cancel_notif = next((n for n in owner_notifs4 if "Review Cancelled: Review 1" in n["title"]), None)
        assert cancel_notif is not None
        assert "cancelled Review 1" in cancel_notif["message"]

        # Verify teammate also received 'Review Cancelled' notification
        notifs_team_res4 = await client.get("/api/v1/notifications", headers=t_headers)
        assert any("Review Cancelled: Review 1" in n["title"] for n in notifs_team_res4.json()["items"])

        # Outsider still has 0 notifications
        notifs_out_final = await client.get("/api/v1/notifications", headers=out_headers)
        assert notifs_out_final.json()["total_count"] == 0

        # =====================================================================
        # 5. MARK NOTIFICATION AS READ
        # =====================================================================
        read_res = await client.patch(f"/api/v1/notifications/{cancel_notif['id']}/read", headers=o_headers)
        assert read_res.status_code == 200
        assert read_res.json()["read_at"] is not None

        # =====================================================================
        # 6. AUTHORIZATION ENFORCEMENT
        # =====================================================================
        # Non-supervisor faculty cannot schedule review (403)
        unauth_fac_schedule = await client.post(
            f"/api/v1/faculty/projects/{project_id}/reviews",
            headers=of_headers,
            json={"review_number": 2, "scheduled_at": review_time_1_str},
        )
        assert unauth_fac_schedule.status_code == 403

        # Non-supervisor faculty cannot reschedule review (403)
        unauth_fac_update = await client.put(
            f"/api/v1/faculty/projects/{project_id}/reviews/{review_1_id}",
            headers=of_headers,
            json={"feedback": "Malicious edit"},
        )
        assert unauth_fac_update.status_code == 403

        # Non-supervisor faculty cannot cancel review (403)
        unauth_fac_cancel = await client.delete(
            f"/api/v1/faculty/projects/{project_id}/reviews/{review_1_id}",
            headers=of_headers,
        )
        assert unauth_fac_cancel.status_code == 403

        # Student cannot schedule or modify reviews (403)
        student_try_schedule = await client.post(
            f"/api/v1/faculty/projects/{project_id}/reviews",
            headers=o_headers,
            json={"review_number": 2, "scheduled_at": review_time_1_str},
        )
        assert student_try_schedule.status_code == 403

    finally:
        owner_uids = [uuid.UUID(uid) for uid in created_users]
        await db_session.execute(delete(ProjectNotification).where(ProjectNotification.recipient_id.in_(owner_uids)))
        await db_session.execute(delete(ProjectReview).where(ProjectReview.faculty_id.in_(owner_uids)))
        await db_session.execute(delete(ProjectMember).where(ProjectMember.user_id.in_(owner_uids)))
        await db_session.execute(delete(AcademicProject).where(AcademicProject.owner_id.in_(owner_uids)))
        for uid in created_users:
            await db_session.execute(delete(User).where(User.id == uuid.UUID(uid)))
        await db_session.commit()
