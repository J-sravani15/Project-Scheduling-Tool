import pytest
import uuid
from datetime import date
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete
from app.models.user import User
from app.models.project import AcademicProject


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
async def test_team_workload_balancing_analysis(client: AsyncClient, db_session: AsyncSession):
    student_a, a_headers = await register_and_login(client, role="student", name="Alice Developer")
    student_b, b_headers = await register_and_login(client, role="student", name="Bob Researcher")

    created_users = [student_a["id"], student_b["id"]]

    try:
        # Create project with Alice as owner
        proj_payload = {
            "title": "Autonomous Robotics Navigation",
            "academic_year": "2025-2026",
            "semester": 8,
            "department": "Robotics Engineering",
            "project_type": "capstone",
            "start_date": "2026-01-10",
            "target_deadline": "2026-06-01",
        }
        p_res = await client.post("/api/v1/projects", json=proj_payload, headers=a_headers)
        assert p_res.status_code == 201, p_res.text
        project_id = p_res.json()["id"]

        # Add Bob as teammate
        await client.post(
            f"/api/v1/projects/{project_id}/members",
            json={"user_id": student_b["id"], "team_role": "member"},
            headers=a_headers,
        )

        # Create Task 1: 30 hours, active, assigned to Alice (overloaded against 25h threshold)
        t1_res = await client.post(
            f"/api/v1/projects/{project_id}/tasks",
            json={
                "title": "SLAM Algorithm Implementation",
                "status": "in_progress",
                "priority": "critical",
                "estimated_duration_hours": 30.0,
                "due_date": "2026-02-01",  # Will be tested as overdue relative to 2026-02-15
            },
            headers=a_headers,
        )
        assert t1_res.status_code == 201
        t1_id = t1_res.json()["id"]
        await client.post(
            f"/api/v1/tasks/{t1_id}/assignments",
            json={"user_id": student_a["id"]},
            headers=a_headers,
        )

        # Create Task 2: 5 hours, active, assigned to Bob (underutilized against 25h threshold)
        t2_res = await client.post(
            f"/api/v1/projects/{project_id}/tasks",
            json={
                "title": "Sensor Calibration",
                "status": "todo",
                "priority": "medium",
                "estimated_duration_hours": 5.0,
                "due_date": "2026-03-01",
            },
            headers=a_headers,
        )
        assert t2_res.status_code == 201
        t2_id = t2_res.json()["id"]
        await client.post(
            f"/api/v1/tasks/{t2_id}/assignments",
            json={"user_id": student_b["id"]},
            headers=a_headers,
        )

        # Create Task 3: 12 hours, completed, assigned to Alice
        t3_res = await client.post(
            f"/api/v1/projects/{project_id}/tasks",
            json={
                "title": "Literature Survey",
                "status": "completed",
                "priority": "low",
                "estimated_duration_hours": 12.0,
                "due_date": "2026-01-25",
            },
            headers=a_headers,
        )
        assert t3_res.status_code == 201
        t3_id = t3_res.json()["id"]
        await client.post(
            f"/api/v1/tasks/{t3_id}/assignments",
            json={"user_id": student_a["id"]},
            headers=a_headers,
        )

        # Analyze workload with reference_date = 2026-02-15 and threshold = 25.0
        wl_res = await client.get(
            f"/api/v1/projects/{project_id}/workload?threshold_hours=25.0&reference_date=2026-02-15",
            headers=a_headers,
        )
        assert wl_res.status_code == 200, wl_res.text
        wl = wl_res.json()

        assert wl["total_team_active_hours"] == 35.0
        assert wl["average_hours_per_student"] == 17.5
        assert wl["workload_standard_deviation"] > 0
        assert student_a["id"] in wl["overloaded_students"]
        assert student_b["id"] in wl["underutilized_students"]

        # Check Alice's workload
        alice_summary = next(s for s in wl["student_workloads"] if s["user_id"] == student_a["id"])
        assert alice_summary["total_active_hours"] == 30.0
        assert alice_summary["completed_hours"] == 12.0
        assert alice_summary["is_overloaded"] is True
        assert alice_summary["overdue_task_count"] == 1  # SLAM Algorithm due 2026-02-01 < 2026-02-15

        # Check Bob's workload
        bob_summary = next(s for s in wl["student_workloads"] if s["user_id"] == student_b["id"])
        assert bob_summary["total_active_hours"] == 5.0
        assert bob_summary["is_underutilized"] is True

        # Check advisory recommendations
        assert len(wl["recommendations"]) > 0
        assert "imbalance" in wl["recommendations"][0].lower()

    finally:
        owner_uids = [uuid.UUID(uid) for uid in created_users]
        await db_session.execute(delete(AcademicProject).where(AcademicProject.owner_id.in_(owner_uids)))
        for uid in created_users:
            await db_session.execute(delete(User).where(User.id == uuid.UUID(uid)))
        await db_session.commit()


@pytest.mark.asyncio
async def test_review_readiness_scoring_engine(client: AsyncClient, db_session: AsyncSession):
    student, s_headers = await register_and_login(client, role="student", name="Lead Researcher")
    faculty, f_headers = await register_and_login(client, role="faculty", name="Reviewer Prof")

    created_users = [student["id"], faculty["id"]]

    try:
        # Create Project
        proj_payload = {
            "title": "Quantum Key Distribution Simulator",
            "academic_year": "2025-2026",
            "semester": 8,
            "department": "Computer Science & Engineering",
            "project_type": "research",
            "start_date": "2026-01-01",
            "target_deadline": "2026-05-30",
            "faculty_guide_id": faculty["id"],
        }
        p_res = await client.post("/api/v1/projects", json=proj_payload, headers=s_headers)
        assert p_res.status_code == 201, p_res.text
        project_id = p_res.json()["id"]

        # 1. Empty project: verify INSUFFICIENT_DATA
        empty_res = await client.get(f"/api/v1/projects/{project_id}/review-readiness", headers=s_headers)
        assert empty_res.status_code == 200
        empty_data = empty_res.json()
        assert empty_data["readiness_level"] == "INSUFFICIENT_DATA"
        assert empty_data["readiness_score"] == 0.0
        assert len(empty_data["blockers"]) > 0

        # 2. Add Milestones
        m1_res = await client.post(
            f"/api/v1/projects/{project_id}/milestones",
            json={
                "title": "Protocol Specification",
                "milestone_type": "project_proposal",
                "sequence_number": 1,
                "planned_date": "2026-02-01",
                "status": "completed",
                "is_required": True,
            },
            headers=s_headers,
        )
        assert m1_res.status_code == 201
        m1_id = m1_res.json()["id"]

        m2_res = await client.post(
            f"/api/v1/projects/{project_id}/milestones",
            json={
                "title": "Simulation Engine",
                "milestone_type": "implementation",
                "sequence_number": 2,
                "planned_date": "2026-04-01",
                "status": "in_progress",
                "is_required": True,
            },
            headers=s_headers,
        )
        assert m2_res.status_code == 201
        m2_id = m2_res.json()["id"]

        # 3. Add Tasks with Critical Path
        t1_res = await client.post(
            f"/api/v1/projects/{project_id}/tasks",
            json={
                "title": "Photon Noise Model",
                "milestone_id": m1_id,
                "status": "completed",
                "priority": "high",
                "estimated_duration_hours": 15.0,
                "due_date": "2026-01-30",
            },
            headers=s_headers,
        )
        assert t1_res.status_code == 201
        t1_id = t1_res.json()["id"]

        t2_res = await client.post(
            f"/api/v1/projects/{project_id}/tasks",
            json={
                "title": "Eavesdropper Interception Simulation",
                "milestone_id": m2_id,
                "status": "in_progress",
                "priority": "critical",
                "estimated_duration_hours": 25.0,
                "due_date": "2026-03-15",
            },
            headers=s_headers,
        )
        assert t2_res.status_code == 201
        t2_id = t2_res.json()["id"]

        # Dependency: t2 depends on t1
        await client.post(
            f"/api/v1/tasks/{t2_id}/dependencies",
            json={"depends_on_task_id": t1_id, "dependency_type": "finish_to_start"},
            headers=s_headers,
        )

        # 4. Schedule Review by Faculty Guide
        rev_res = await client.post(
            f"/api/v1/faculty/projects/{project_id}/reviews",
            json={
                "review_number": 1,
                "scheduled_at": "2026-03-25T10:00:00Z",
                "status": "scheduled",
            },
            headers=f_headers,
        )
        assert rev_res.status_code == 201

        # 5. Evaluate Readiness
        eval_res = await client.get(
            f"/api/v1/projects/{project_id}/review-readiness?reference_date=2026-02-15",
            headers=s_headers,
        )
        assert eval_res.status_code == 200, eval_res.text
        eval_data = eval_res.json()

        assert eval_data["readiness_score"] > 0
        breakdown = eval_data["score_breakdown"]
        # Milestone: 1 of 2 required completed = 50% of 40 = 20.0
        assert breakdown["milestone_score"] == 20.0
        # Task completion: 1 of 2 completed = 50% of 15 = 7.5
        assert breakdown["task_completion_score"] == 7.5
        # Total score matches sum
        expected_total = (
            breakdown["milestone_score"]
            + breakdown["task_completion_score"]
            + breakdown["critical_path_score"]
            + breakdown["overdue_score"]
            + breakdown["review_timing_score"]
        )
        assert abs(eval_data["readiness_score"] - expected_total) < 0.1
        assert eval_data["next_review_scheduled_at"] is not None

        # 6. Verify Overdue Blocker Detection:
        # If reference date is 2026-04-10 (past m2's planned date 2026-04-01), m2 is overdue
        overdue_eval = await client.get(
            f"/api/v1/projects/{project_id}/review-readiness?reference_date=2026-04-10",
            headers=s_headers,
        )
        assert overdue_eval.status_code == 200
        overdue_data = overdue_eval.json()
        assert any("overdue" in b.lower() and "simulation engine" in b.lower() for b in overdue_data["blockers"])

    finally:
        owner_uids = [uuid.UUID(uid) for uid in created_users]
        await db_session.execute(delete(AcademicProject).where(AcademicProject.owner_id.in_(owner_uids)))
        for uid in created_users:
            await db_session.execute(delete(User).where(User.id == uuid.UUID(uid)))
        await db_session.commit()
