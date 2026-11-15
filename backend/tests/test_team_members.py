import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete
from app.models.user import User
from app.models.project import AcademicProject, ProjectMember


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


async def create_test_project(client: AsyncClient, headers: dict, title: str = "Team Project"):
    res = await client.post(
        "/api/v1/projects",
        headers=headers,
        json={
            "title": title,
            "description": "Project for testing team member operations",
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
async def test_list_students_endpoint(client: AsyncClient, db_session: AsyncSession):
    """
    Verifies that GET /api/v1/students returns active students, excludes faculty,
    and supports search by name or email.
    """
    student_1, s1_headers = await register_and_login(client, role="student", name="Kavya Student")
    student_2, s2_headers = await register_and_login(client, role="student", name="Rahul Student")
    faculty_user, f_headers = await register_and_login(client, role="faculty", name="Dr. Raman")

    try:
        # Student listing accessible to authenticated users
        res = await client.get("/api/v1/students", headers=s1_headers)
        assert res.status_code == 200, res.text
        data = res.json()
        assert isinstance(data, list)

        student_ids = [s["id"] for s in data]
        assert student_1["id"] in student_ids
        assert student_2["id"] in student_ids
        assert faculty_user["id"] not in student_ids  # Faculty must be excluded

        # Check search by name
        res_search_name = await client.get("/api/v1/students?search=Kavya", headers=s1_headers)
        assert res_search_name.status_code == 200
        search_data = res_search_name.json()
        assert any(s["id"] == student_1["id"] for s in search_data)
        assert not any(s["id"] == student_2["id"] for s in search_data)

        # Check search by email prefix
        email_prefix = student_2["email"].split("@")[0]
        res_search_email = await client.get(f"/api/v1/students?search={email_prefix}", headers=s1_headers)
        assert res_search_email.status_code == 200
        search_email_data = res_search_email.json()
        assert any(s["id"] == student_2["id"] for s in search_email_data)

    finally:
        await db_session.execute(
            delete(User).where(User.id.in_([
                uuid.UUID(student_1["id"]),
                uuid.UUID(student_2["id"]),
                uuid.UUID(faculty_user["id"]),
            ]))
        )
        await db_session.commit()


@pytest.mark.asyncio
async def test_list_available_students_filters_correctly(client: AsyncClient, db_session: AsyncSession):
    """
    Verifies GET /api/v1/projects/{project_id}/available-students excludes:
    1. The project owner
    2. Enrolled project members
    3. Faculty members
    And includes eligible students.
    """
    owner, o_headers = await register_and_login(client, role="student", name="Owner Student")
    member_student, m_headers = await register_and_login(client, role="student", name="Enrolled Member")
    eligible_student, _ = await register_and_login(client, role="student", name="Available Student")
    faculty_user, _ = await register_and_login(client, role="faculty", name="Faculty Guide")

    project = await create_test_project(client, o_headers, title="Available Students Test Project")
    project_id = project["id"]

    try:
        # Add member_student to the project
        add_res = await client.post(
            f"/api/v1/projects/{project_id}/members",
            headers=o_headers,
            json={"user_id": member_student["id"], "team_role": "developer"},
        )
        assert add_res.status_code == 201, add_res.text

        # Fetch available students
        res = await client.get(f"/api/v1/projects/{project_id}/available-students", headers=o_headers)
        assert res.status_code == 200, res.text
        avail = res.json()
        avail_ids = [s["id"] for s in avail]

        # Eligible student should be present
        assert eligible_student["id"] in avail_ids
        # Project owner should NOT be in available students
        assert owner["id"] not in avail_ids
        # Already enrolled member should NOT be in available students
        assert member_student["id"] not in avail_ids
        # Faculty should NOT be in available students
        assert faculty_user["id"] not in avail_ids

    finally:
        await db_session.execute(delete(ProjectMember).where(ProjectMember.project_id == uuid.UUID(project_id)))
        await db_session.execute(delete(AcademicProject).where(AcademicProject.id == uuid.UUID(project_id)))
        await db_session.execute(
            delete(User).where(User.id.in_([
                uuid.UUID(owner["id"]),
                uuid.UUID(member_student["id"]),
                uuid.UUID(eligible_student["id"]),
                uuid.UUID(faculty_user["id"]),
            ]))
        )
        await db_session.commit()


@pytest.mark.asyncio
async def test_add_team_member_authorization_and_validation(client: AsyncClient, db_session: AsyncSession):
    """
    Verifies adding team members:
    - Success with 201
    - Duplicate rejected with 400
    - Faculty user rejected with 400
    - Adding owner rejected with 400
    - Non-owner forbidden with 403
    """
    owner, o_headers = await register_and_login(client, role="student", name="Project Lead")
    other_student, other_headers = await register_and_login(client, role="student", name="Other Student")
    new_member, _ = await register_and_login(client, role="student", name="New Member Student")
    faculty_user, _ = await register_and_login(client, role="faculty", name="Faculty Member")

    project = await create_test_project(client, o_headers, title="Validation Test Project")
    project_id = project["id"]

    try:
        # 1. Non-owner cannot add members -> 403
        forbidden_res = await client.post(
            f"/api/v1/projects/{project_id}/members",
            headers=other_headers,
            json={"user_id": new_member["id"], "team_role": "developer"},
        )
        assert forbidden_res.status_code == 403, forbidden_res.text

        # 2. Cannot add faculty as team member -> 400
        faculty_res = await client.post(
            f"/api/v1/projects/{project_id}/members",
            headers=o_headers,
            json={"user_id": faculty_user["id"], "team_role": "researcher"},
        )
        assert faculty_res.status_code == 400, faculty_res.text
        assert "Faculty members cannot be added" in faculty_res.text

        # 3. Cannot add project owner as member -> 400
        owner_res = await client.post(
            f"/api/v1/projects/{project_id}/members",
            headers=o_headers,
            json={"user_id": owner["id"], "team_role": "developer"},
        )
        assert owner_res.status_code == 400, owner_res.text

        # 4. Successful addition by owner -> 201
        success_res = await client.post(
            f"/api/v1/projects/{project_id}/members",
            headers=o_headers,
            json={"user_id": new_member["id"], "team_role": "tester"},
        )
        assert success_res.status_code == 201, success_res.text
        created_data = success_res.json()
        assert created_data["user_id"] == new_member["id"]
        assert created_data["team_role"] == "tester"
        assert created_data["user"]["full_name"] == "New Member Student"
        assert created_data["user"]["email"] == new_member["email"]

        # 5. Adding duplicate student -> 400
        duplicate_res = await client.post(
            f"/api/v1/projects/{project_id}/members",
            headers=o_headers,
            json={"user_id": new_member["id"], "team_role": "developer"},
        )
        assert duplicate_res.status_code == 400, duplicate_res.text
        assert "already a member" in duplicate_res.text

    finally:
        await db_session.execute(delete(ProjectMember).where(ProjectMember.project_id == uuid.UUID(project_id)))
        await db_session.execute(delete(AcademicProject).where(AcademicProject.id == uuid.UUID(project_id)))
        await db_session.execute(
            delete(User).where(User.id.in_([
                uuid.UUID(owner["id"]),
                uuid.UUID(other_student["id"]),
                uuid.UUID(new_member["id"]),
                uuid.UUID(faculty_user["id"]),
            ]))
        )
        await db_session.commit()
