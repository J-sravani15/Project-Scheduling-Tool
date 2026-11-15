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
async def test_list_faculty_members(client: AsyncClient, db_session: AsyncSession):
    """
    Verifies that GET /api/v1/faculty lists all registered active faculty members
    with only safe UserSummary fields (id, full_name, email, role).
    """
    faculty_user, f_headers = await register_and_login(client, role="faculty", name="Prof. Homi Bhabha")
    student_user, s_headers = await register_and_login(client, role="student", name="Vikram Student")

    try:
        # Accessible to authenticated student
        res = await client.get("/api/v1/faculty", headers=s_headers)
        assert res.status_code == 200, res.text
        data = res.json()
        assert isinstance(data, list)
        assert len(data) >= 1

        # Check every entry is faculty and contains only safe fields
        faculty_ids = [f["id"] for f in data]
        assert faculty_user["id"] in faculty_ids
        assert student_user["id"] not in faculty_ids  # Students must not appear

        # Validate fields
        homi = next(f for f in data if f["id"] == faculty_user["id"])
        assert homi["full_name"] == "Prof. Homi Bhabha"
        assert homi["role"] == "faculty"
        assert "password" not in homi
        assert "password_hash" not in homi

    finally:
        await db_session.execute(delete(User).where(User.id.in_([uuid.UUID(faculty_user["id"]), uuid.UUID(student_user["id"])])))
        await db_session.commit()


@pytest.mark.asyncio
async def test_assign_faculty_guide_flow(client: AsyncClient, db_session: AsyncSession):
    """
    Tests the full guide assignment flow:
    1. Student creates project with no guide.
    2. Owner assigns valid faculty member -> 200 OK.
    3. Project details reflects assigned faculty supervisor.
    4. Faculty dashboard includes the newly assigned project.
    """
    faculty_user, f_headers = await register_and_login(client, role="faculty", name="Dr. APJ Kalam")
    student_owner, o_headers = await register_and_login(client, role="student", name="ISRO Aspirant")

    # 1. Create project with no faculty guide
    proj_res = await client.post(
        "/api/v1/projects",
        json={
            "title": "Satellite Trajectory Planning Tool",
            "academic_year": "2025-2026",
            "semester": 8,
            "department": "Aerospace & Computing",
            "project_type": "capstone",
            "start_date": "2026-01-15",
            "target_deadline": "2026-05-30",
        },
        headers=o_headers,
    )
    assert proj_res.status_code == 201
    proj_id = proj_res.json()["id"]
    assert proj_res.json()["faculty_guide_id"] is None

    try:
        # Verify faculty initially has no projects assigned
        fac_projects_before = await client.get("/api/v1/faculty/projects", headers=f_headers)
        assert fac_projects_before.status_code == 200
        before_ids = [p["id"] for p in fac_projects_before.json()]
        assert proj_id not in before_ids

        # 2. Assign faculty guide via PUT /projects/{id}/faculty-guide
        assign_res = await client.put(
            f"/api/v1/projects/{proj_id}/faculty-guide",
            json={"faculty_guide_id": faculty_user["id"]},
            headers=o_headers,
        )
        assert assign_res.status_code == 200, assign_res.text
        updated_proj = assign_res.json()
        assert updated_proj["faculty_guide_id"] == faculty_user["id"]
        assert updated_proj["faculty_guide"]["id"] == faculty_user["id"]
        assert updated_proj["faculty_guide"]["full_name"] == "Dr. APJ Kalam"

        # 3. GET project overview also reflects the assigned supervisor
        get_proj = await client.get(f"/api/v1/projects/{proj_id}", headers=o_headers)
        assert get_proj.status_code == 200
        assert get_proj.json()["faculty_guide"]["full_name"] == "Dr. APJ Kalam"

        # 4. Assigned project now appears on faculty's dashboard
        fac_projects_after = await client.get("/api/v1/faculty/projects", headers=f_headers)
        assert fac_projects_after.status_code == 200
        after_ids = [p["id"] for p in fac_projects_after.json()]
        assert proj_id in after_ids

    finally:
        await db_session.execute(delete(AcademicProject).where(AcademicProject.id == uuid.UUID(proj_id)))
        await db_session.execute(delete(User).where(User.id.in_([uuid.UUID(faculty_user["id"]), uuid.UUID(student_owner["id"])])))
        await db_session.commit()


@pytest.mark.asyncio
async def test_assign_faculty_guide_validation_and_rbac(client: AsyncClient, db_session: AsyncSession):
    """
    Verifies error cases:
    - Non-faculty user ID -> 400 Bad Request
    - Nonexistent faculty user ID -> 400 Bad Request
    - Non-owner user attempting to assign -> 403 Forbidden
    - Nonexistent project -> 404 Not Found
    """
    faculty_user, f_headers = await register_and_login(client, role="faculty", name="Valid Guide")
    student_owner, o_headers = await register_and_login(client, role="student", name="Legit Owner")
    unauthorized_student, u_headers = await register_and_login(client, role="student", name="Other Student")

    proj_res = await client.post(
        "/api/v1/projects",
        json={
            "title": "Quantum Key Distribution",
            "academic_year": "2025-2026",
            "semester": 8,
            "department": "CSE",
            "project_type": "research",
            "start_date": "2026-02-01",
            "target_deadline": "2026-06-01",
        },
        headers=o_headers,
    )
    assert proj_res.status_code == 201
    proj_id = proj_res.json()["id"]

    try:
        # 1. Reject student ID as faculty supervisor (400)
        rej_student = await client.put(
            f"/api/v1/projects/{proj_id}/faculty-guide",
            json={"faculty_guide_id": unauthorized_student["id"]},
            headers=o_headers,
        )
        assert rej_student.status_code == 400
        assert "must be an existing user with faculty role" in rej_student.json()["detail"].lower()

        # 2. Reject nonexistent UUID (400)
        fake_uuid = str(uuid.uuid4())
        rej_fake = await client.put(
            f"/api/v1/projects/{proj_id}/faculty-guide",
            json={"faculty_guide_id": fake_uuid},
            headers=o_headers,
        )
        assert rej_fake.status_code == 400
        assert "must be an existing user with faculty role" in rej_fake.json()["detail"].lower()

        # 3. Reject assignment by unauthorized student (403)
        rej_unauthorized = await client.put(
            f"/api/v1/projects/{proj_id}/faculty-guide",
            json={"faculty_guide_id": faculty_user["id"]},
            headers=u_headers,
        )
        assert rej_unauthorized.status_code == 403

        # 4. Reject nonexistent project (404)
        fake_proj_id = str(uuid.uuid4())
        rej_proj = await client.put(
            f"/api/v1/projects/{fake_proj_id}/faculty-guide",
            json={"faculty_guide_id": faculty_user["id"]},
            headers=o_headers,
        )
        assert rej_proj.status_code == 404

    finally:
        await db_session.execute(delete(AcademicProject).where(AcademicProject.id == uuid.UUID(proj_id)))
        await db_session.execute(delete(User).where(User.id.in_([
            uuid.UUID(faculty_user["id"]),
            uuid.UUID(student_owner["id"]),
            uuid.UUID(unauthorized_student["id"])
        ])))
        await db_session.commit()
