import pytest
import uuid
from datetime import date, datetime, timedelta, timezone
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.models.user import User
from app.models.project import AcademicProject, ProjectMember
from app.models.milestone import AcademicMilestone
from app.models.task import Task, TaskAssignment, TaskDependency
from app.models.enums import TaskStatus, TaskPriority, MilestoneStatus, MilestoneType, TeamRole


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
async def test_milestone_and_task_edit_delete_lifecycle(client: AsyncClient, db_session: AsyncSession):
    """
    Verifies full lifecycle of:
    1. Milestone editing (title, planned_date, sequence, required/optional toggle).
    2. Milestone deletion (and tasks attached have milestone_id set to NULL).
    3. Task editing (title, duration, priority, due date, milestone link).
    4. Task deletion (clean cascade of assignments and dependencies).
    5. Project details editing.
    6. Member role update and member removal.
    7. Authorization enforcement (403 for unauthorized users).
    """
    owner, o_headers = await register_and_login(client, role="student", name="Owner Lead")
    teammate, t_headers = await register_and_login(client, role="student", name="Dev Student")
    outsider, out_headers = await register_and_login(client, role="student", name="Outsider Student")

    created_users = [owner["id"], teammate["id"], outsider["id"]]

    try:
        # Create Project
        p_res = await client.post(
            "/api/v1/projects",
            headers=o_headers,
            json={
                "title": "Robotics Navigation Platform",
                "description": "Autonomous path planning and SLAM",
                "academic_year": "2026-2027",
                "semester": 8,
                "department": "Robotics",
                "project_type": "capstone",
                "start_date": "2026-01-15",
                "target_deadline": "2026-05-30",
            },
        )
        assert p_res.status_code == 201, p_res.text
        project_id = p_res.json()["id"]

        # Add Teammate
        m_res = await client.post(
            f"/api/v1/projects/{project_id}/members",
            headers=o_headers,
            json={"user_id": teammate["id"], "team_role": "developer"},
        )
        assert m_res.status_code == 201, m_res.text

        # =====================================================================
        # 1. MILESTONE CREATION, EDITING & REQUIRED TOGGLE
        # =====================================================================
        m1_res = await client.post(
            f"/api/v1/projects/{project_id}/milestones",
            headers=o_headers,
            json={
                "title": "Literature Review & Proposal",
                "description": "Initial proposal defense",
                "milestone_type": "project_proposal",
                "sequence_number": 1,
                "planned_date": "2026-02-15",
                "status": "pending",
                "is_required": True,
            },
        )
        assert m1_res.status_code == 201, m1_res.text
        m1 = m1_res.json()
        assert m1["is_required"] is True

        m2_res = await client.post(
            f"/api/v1/projects/{project_id}/milestones",
            headers=o_headers,
            json={
                "title": "Hardware Setup & Sensors",
                "milestone_type": "custom",
                "sequence_number": 2,
                "planned_date": "2026-03-10",
                "status": "pending",
                "is_required": False,
            },
        )
        assert m2_res.status_code == 201, m2_res.text
        m2 = m2_res.json()
        assert m2["is_required"] is False

        # Edit milestone 1: change title, planned_date, and toggle is_required to False
        m1_update_res = await client.put(
            f"/api/v1/milestones/{m1['id']}",
            headers=o_headers,
            json={
                "title": "Updated Proposal & Literature Review",
                "planned_date": "2026-02-20",
                "is_required": False,
            },
        )
        assert m1_update_res.status_code == 200, m1_update_res.text
        m1_updated = m1_update_res.json()
        assert m1_updated["title"] == "Updated Proposal & Literature Review"
        assert m1_updated["planned_date"] == "2026-02-20"
        assert m1_updated["is_required"] is False
        assert m1_updated["status"] == "pending"  # Did NOT mark completed simply because edited

        # Edit milestone 2: test duplicate sequence number validation
        m2_dup_seq = await client.put(
            f"/api/v1/milestones/{m2['id']}",
            headers=o_headers,
            json={"sequence_number": 1},  # already taken by m1
        )
        assert m2_dup_seq.status_code == 400
        assert "already exists" in m2_dup_seq.text

        # =====================================================================
        # 2. TASK CREATION, EDITING & DEPENDENCY SAFEGUARDS
        # =====================================================================
        # Create Task A attached to Milestone 1
        t_a_res = await client.post(
            f"/api/v1/projects/{project_id}/tasks",
            headers=o_headers,
            json={
                "title": "Sensor Calibration",
                "description": "Calibrate IMU and LiDAR",
                "milestone_id": m1["id"],
                "status": "todo",
                "priority": "high",
                "estimated_duration_hours": 12.0,
                "start_date": "2026-02-01",
                "due_date": "2026-02-14",
            },
        )
        assert t_a_res.status_code == 201, t_a_res.text
        task_a = t_a_res.json()
        assert task_a["milestone_id"] == m1["id"]

        # Create Task B
        t_b_res = await client.post(
            f"/api/v1/projects/{project_id}/tasks",
            headers=o_headers,
            json={
                "title": "SLAM Node Implementation",
                "status": "todo",
                "priority": "critical",
                "estimated_duration_hours": 20.0,
                "due_date": "2026-03-01",
            },
        )
        assert t_b_res.status_code == 201, t_b_res.text
        task_b = t_b_res.json()

        # Assign teammate to Task A
        assign_res = await client.post(
            f"/api/v1/tasks/{task_a['id']}/assignments",
            headers=o_headers,
            json={"user_id": teammate["id"]},
        )
        assert assign_res.status_code == 201, assign_res.text

        # Add dependency: Task B depends on Task A
        dep_res = await client.post(
            f"/api/v1/tasks/{task_b['id']}/dependencies",
            headers=o_headers,
            json={"depends_on_task_id": task_a["id"]},
        )
        assert dep_res.status_code == 201, dep_res.text

        # Edit Task A: change title, duration, priority, due date
        t_a_update_res = await client.put(
            f"/api/v1/tasks/{task_a['id']}",
            headers=o_headers,
            json={
                "title": "Calibrate All LiDAR and IMU Sensors",
                "priority": "critical",
                "estimated_duration_hours": 16.0,
                "due_date": "2026-02-18",
            },
        )
        assert t_a_update_res.status_code == 200, t_a_update_res.text
        t_a_updated = t_a_update_res.json()
        assert t_a_updated["title"] == "Calibrate All LiDAR and IMU Sensors"
        assert t_a_updated["priority"] == "critical"
        assert t_a_updated["estimated_duration_hours"] == 16.0
        assert t_a_updated["due_date"] == "2026-02-18"

        # =====================================================================
        # 3. MILESTONE DELETION & TASK SAFETY
        # =====================================================================
        del_m1_res = await client.delete(f"/api/v1/milestones/{m1['id']}", headers=o_headers)
        assert del_m1_res.status_code == 204

        # Task A should still exist, but milestone_id should be set to None
        t_a_check = await client.get(f"/api/v1/tasks/{task_a['id']}", headers=o_headers)
        assert t_a_check.status_code == 200
        assert t_a_check.json()["milestone_id"] is None

        # =====================================================================
        # 4. TASK DELETION & DEPENDENCY/ASSIGNMENT CASCADE
        # =====================================================================
        # Deleting Task A should cleanly remove its assignment and dependency on Task B
        del_t_a_res = await client.delete(f"/api/v1/tasks/{task_a['id']}", headers=o_headers)
        assert del_t_a_res.status_code == 204

        # Verify Task A is 404
        assert (await client.get(f"/api/v1/tasks/{task_a['id']}", headers=o_headers)).status_code == 404

        # Verify Task B is still intact and CPM calculations work without error
        cpm_res = await client.get(f"/api/v1/projects/{project_id}/schedule/cpm", headers=o_headers)
        assert cpm_res.status_code == 200

        # =====================================================================
        # 5. PROJECT EDITING & MEMBER ROLES
        # =====================================================================
        # Owner edits project details
        proj_edit_res = await client.put(
            f"/api/v1/projects/{project_id}",
            headers=o_headers,
            json={
                "title": "Advanced Robotics Navigation Platform",
                "description": "Multi-agent SLAM and optimal control",
                "target_deadline": "2026-06-15",
            },
        )
        assert proj_edit_res.status_code == 200, proj_edit_res.text
        proj_updated = proj_edit_res.json()
        assert proj_updated["title"] == "Advanced Robotics Navigation Platform"
        assert proj_updated["target_deadline"] == "2026-06-15"

        # Update teammate role
        role_res = await client.put(
            f"/api/v1/projects/{project_id}/members/{teammate['id']}",
            headers=o_headers,
            json={"team_role": "tester"},
        )
        assert role_res.status_code == 200, role_res.text
        assert role_res.json()["team_role"] == "tester"

        # Try to remove owner (must fail with 400)
        remove_owner_res = await client.delete(
            f"/api/v1/projects/{project_id}/members/{owner['id']}",
            headers=o_headers,
        )
        assert remove_owner_res.status_code == 400
        assert "owner/leader cannot be removed" in remove_owner_res.text

        # Remove teammate (must succeed)
        remove_tm_res = await client.delete(
            f"/api/v1/projects/{project_id}/members/{teammate['id']}",
            headers=o_headers,
        )
        assert remove_tm_res.status_code == 204

        # =====================================================================
        # 6. AUTHORIZATION ENFORCEMENT
        # =====================================================================
        # Outsider cannot edit or delete project
        assert (await client.put(f"/api/v1/projects/{project_id}", headers=out_headers, json={"title": "Hacked"})).status_code == 403
        assert (await client.delete(f"/api/v1/projects/{project_id}", headers=out_headers)).status_code == 403
        assert (await client.delete(f"/api/v1/milestones/{m2['id']}", headers=out_headers)).status_code == 403
        assert (await client.delete(f"/api/v1/tasks/{task_b['id']}", headers=out_headers)).status_code == 403

        # Clean delete project by owner
        del_proj = await client.delete(f"/api/v1/projects/{project_id}", headers=o_headers)
        assert del_proj.status_code == 204

    finally:
        owner_uids = [uuid.UUID(uid) for uid in created_users]
        await db_session.execute(delete(TaskAssignment).where(TaskAssignment.user_id.in_(owner_uids)))
        await db_session.execute(delete(ProjectMember).where(ProjectMember.user_id.in_(owner_uids)))
        await db_session.execute(delete(AcademicProject).where(AcademicProject.owner_id.in_(owner_uids)))
        for uid in created_users:
            await db_session.execute(delete(User).where(User.id == uuid.UUID(uid)))
        await db_session.commit()
