import pytest
import uuid
from datetime import date, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete
from app.models.user import User
from app.models.project import AcademicProject
from app.models.milestone import AcademicMilestone


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
async def test_milestone_status_transition_and_readiness_scoring(client: AsyncClient, db_session: AsyncSession):
    owner, headers = await register_and_login(client, role="student", name="Project Lead")
    created_users = [owner["id"]]

    try:
        # 1. Create a project
        p_res = await client.post(
            "/api/v1/projects",
            json={
                "title": f"Milestone Status Project {uuid.uuid4().hex[:6]}",
                "academic_year": "2025-2026",
                "semester": 7,
                "department": "Computer Science",
                "project_type": "capstone",
                "start_date": "2026-01-01",
                "target_deadline": "2026-06-01",
            },
            headers=headers,
        )
        assert p_res.status_code == 201, p_res.text
        project_id = p_res.json()["id"]

        # 2. Create Milestone 1 (Planned in future, required=True, no status specified -> defaults to pending)
        future_date = (date.today() + timedelta(days=30)).isoformat()
        m1_res = await client.post(
            f"/api/v1/projects/{project_id}/milestones",
            json={
                "title": "Topic Selection & Proposal",
                "sequence_number": 1,
                "milestone_type": "topic_selection",
                "planned_date": future_date,
                "is_required": True,
            },
            headers=headers,
        )
        assert m1_res.status_code == 201, m1_res.text
        m1 = m1_res.json()
        assert m1["status"] == "pending"
        assert m1["completed_at"] is None

        # 3. Create Milestone 2 (Required=True, status="pending")
        m2_res = await client.post(
            f"/api/v1/projects/{project_id}/milestones",
            json={
                "title": "System Design Review",
                "sequence_number": 2,
                "milestone_type": "system_design",
                "planned_date": future_date,
                "status": "pending",
                "is_required": True,
            },
            headers=headers,
        )
        assert m2_res.status_code == 201, m2_res.text
        m2 = m2_res.json()
        assert m2["status"] == "pending"

        # 4. Check readiness score when both are pending -> milestone_score must be 0.0
        readiness_res = await client.get(
            f"/api/v1/projects/{project_id}/review-readiness",
            headers=headers,
        )
        assert readiness_res.status_code == 200, readiness_res.text
        readiness_data = readiness_res.json()
        assert readiness_data["score_breakdown"]["milestone_score"] == 0.0

        # 5. Update Milestone 1 to 'completed' via PUT /milestones/{id}
        put_res = await client.put(
            f"/api/v1/milestones/{m1['id']}",
            json={
                "title": "Topic Selection & Proposal",
                "sequence_number": 1,
                "status": "completed",
            },
            headers=headers,
        )
        assert put_res.status_code == 200, put_res.text
        updated_m1 = put_res.json()
        assert updated_m1["status"] == "completed"
        assert updated_m1["completed_at"] is not None

        # 6. Check readiness score now: 1 of 2 required milestones completed -> milestone_score = 20.0
        readiness_res2 = await client.get(
            f"/api/v1/projects/{project_id}/review-readiness",
            headers=headers,
        )
        assert readiness_res2.status_code == 200, readiness_res2.text
        assert readiness_res2.json()["score_breakdown"]["milestone_score"] == 20.0

        # 7. Update Milestone 2 to 'completed' via PATCH /milestones/{id}/status
        patch_res = await client.patch(
            f"/api/v1/milestones/{m2['id']}/status?status_value=completed",
            headers=headers,
        )
        assert patch_res.status_code == 200, patch_res.text
        assert patch_res.json()["status"] == "completed"
        assert patch_res.json()["completed_at"] is not None

        # 8. Check readiness score now: 2 of 2 required milestones completed -> milestone_score = 40.0
        readiness_res3 = await client.get(
            f"/api/v1/projects/{project_id}/review-readiness",
            headers=headers,
        )
        assert readiness_res3.status_code == 200, readiness_res3.text
        assert readiness_res3.json()["score_breakdown"]["milestone_score"] == 40.0

        # 9. Toggle Milestone 1 back from 'completed' to 'pending' via PUT /milestones/{id}
        put_pending_res = await client.put(
            f"/api/v1/milestones/{m1['id']}",
            json={
                "status": "pending",
            },
            headers=headers,
        )
        assert put_pending_res.status_code == 200, put_pending_res.text
        reverted_m1 = put_pending_res.json()
        assert reverted_m1["status"] == "pending"
        assert reverted_m1["completed_at"] is None

        # 10. Check readiness score: 1 of 2 completed -> milestone_score back to 20.0
        readiness_res4 = await client.get(
            f"/api/v1/projects/{project_id}/review-readiness",
            headers=headers,
        )
        assert readiness_res4.status_code == 200, readiness_res4.text
        assert readiness_res4.json()["score_breakdown"]["milestone_score"] == 20.0

        # 11. Toggle Milestone 2 back to 'pending' via PATCH
        patch_pending_res = await client.patch(
            f"/api/v1/milestones/{m2['id']}/status?status_value=pending",
            headers=headers,
        )
        assert patch_pending_res.status_code == 200, patch_pending_res.text
        assert patch_pending_res.json()["status"] == "pending"
        assert patch_pending_res.json()["completed_at"] is None

        # 12. Check readiness score: 0 of 2 completed -> milestone_score back to 0.0
        readiness_res5 = await client.get(
            f"/api/v1/projects/{project_id}/review-readiness",
            headers=headers,
        )
        assert readiness_res5.status_code == 200, readiness_res5.text
        assert readiness_res5.json()["score_breakdown"]["milestone_score"] == 0.0

    finally:
        if project_id:
            await db_session.execute(delete(AcademicProject).where(AcademicProject.id == uuid.UUID(project_id)))
        for uid in created_users:
            await db_session.execute(delete(User).where(User.id == uuid.UUID(uid)))
        await db_session.commit()
