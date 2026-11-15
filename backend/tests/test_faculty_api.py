import pytest
import uuid
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
async def test_faculty_monitoring_and_review_flow(client: AsyncClient, db_session: AsyncSession):
    # Setup Faculty 1, Faculty 2, and Student
    faculty_1, f1_headers = await register_and_login(client, role="faculty", name="Dr. Ramanujan")
    faculty_2, f2_headers = await register_and_login(client, role="faculty", name="Dr. Aryabhata")
    student_1, s1_headers = await register_and_login(client, role="student", name="Srinivasa Student")

    created_users = [faculty_1["id"], faculty_2["id"], student_1["id"]]

    try:
        # 1. Student creates Project 1 supervised by Faculty 1
        p1_res = await client.post(
            "/api/v1/projects",
            json={
                "title": "Compiler Optimization for RISC-V",
                "academic_year": "2025-2026",
                "semester": 8,
                "department": "Computer Science & Engineering",
                "project_type": "capstone",
                "start_date": "2026-01-10",
                "target_deadline": "2026-05-15",
                "faculty_guide_id": faculty_1["id"],
            },
            headers=s1_headers,
        )
        assert p1_res.status_code == 201, p1_res.text
        p1_id = p1_res.json()["id"]

        # 2. Student creates Project 2 supervised by Faculty 2
        p2_res = await client.post(
            "/api/v1/projects",
            json={
                "title": "Post-Quantum Cryptography Schemes",
                "academic_year": "2025-2026",
                "semester": 8,
                "department": "Computer Science & Engineering",
                "project_type": "research",
                "start_date": "2026-01-10",
                "target_deadline": "2026-05-15",
                "faculty_guide_id": faculty_2["id"],
            },
            headers=s1_headers,
        )
        assert p2_res.status_code == 201, p2_res.text
        p2_id = p2_res.json()["id"]

        # 3. Student attempting to access faculty endpoint is rejected (403 Forbidden)
        student_try_fac = await client.get("/api/v1/faculty/projects", headers=s1_headers)
        assert student_try_fac.status_code == 403
        assert "faculty" in student_try_fac.json()["detail"].lower()

        # 4. Faculty 1 lists supervised projects (sees P1, but NOT P2)
        f1_list = await client.get("/api/v1/faculty/projects", headers=f1_headers)
        assert f1_list.status_code == 200
        f1_projects = f1_list.json()
        assert any(p["id"] == p1_id for p in f1_projects)
        assert not any(p["id"] == p2_id for p in f1_projects)

        # 5. Faculty 2 lists supervised projects (sees P2, but NOT P1)
        f2_list = await client.get("/api/v1/faculty/projects", headers=f2_headers)
        assert f2_list.status_code == 200
        f2_projects = f2_list.json()
        assert any(p["id"] == p2_id for p in f2_projects)
        assert not any(p["id"] == p1_id for p in f2_projects)

        # 6. Faculty 1 accesses overview for Project 1 (200 OK)
        f1_overview = await client.get(f"/api/v1/faculty/projects/{p1_id}/overview", headers=f1_headers)
        assert f1_overview.status_code == 200, f1_overview.text
        data = f1_overview.json()
        assert data["project"]["id"] == p1_id
        assert "workload" in data
        assert "readiness" in data
        assert "reviews" in data

        # 7. Faculty 2 attempting to access Project 1's overview is strictly rejected (403 Forbidden)
        f2_try_p1 = await client.get(f"/api/v1/faculty/projects/{p1_id}/overview", headers=f2_headers)
        assert f2_try_p1.status_code == 403
        assert "not the assigned faculty guide" in f2_try_p1.json()["detail"].lower()

        # 8. Non-existent project overview returns 404 Not Found
        random_uuid = str(uuid.uuid4())
        f1_404 = await client.get(f"/api/v1/faculty/projects/{random_uuid}/overview", headers=f1_headers)
        assert f1_404.status_code == 404

        # 9. Faculty 1 schedules Review 1 for Project 1
        rev_payload = {
            "review_number": 1,
            "scheduled_at": "2026-03-10T14:00:00Z",
            "status": "scheduled",
            "feedback": "Preliminary design review presentation",
        }
        rev_res = await client.post(
            f"/api/v1/faculty/projects/{p1_id}/reviews",
            json=rev_payload,
            headers=f1_headers,
        )
        assert rev_res.status_code == 201, rev_res.text
        review_data = rev_res.json()
        assert review_data["review_number"] == 1
        assert review_data["faculty"]["id"] == faculty_1["id"]

        # Duplicate review number rejected
        dup_rev = await client.post(
            f"/api/v1/faculty/projects/{p1_id}/reviews",
            json=rev_payload,
            headers=f1_headers,
        )
        assert dup_rev.status_code == 400

        # Faculty 2 cannot conduct review for Project 1 (403 Forbidden)
        f2_conduct = await client.post(
            f"/api/v1/faculty/projects/{p1_id}/reviews",
            json={"review_number": 2, "scheduled_at": "2026-04-10T14:00:00Z"},
            headers=f2_headers,
        )
        assert f2_conduct.status_code == 403

        # Student cannot conduct reviews (403 Forbidden)
        student_conduct = await client.post(
            f"/api/v1/faculty/projects/{p1_id}/reviews",
            json={"review_number": 2, "scheduled_at": "2026-04-10T14:00:00Z"},
            headers=s1_headers,
        )
        assert student_conduct.status_code == 403

    finally:
        owner_uids = [uuid.UUID(uid) for uid in created_users]
        await db_session.execute(delete(AcademicProject).where(AcademicProject.owner_id.in_(owner_uids)))
        for uid in created_users:
            await db_session.execute(delete(User).where(User.id == uuid.UUID(uid)))
        await db_session.commit()
