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
async def test_project_crud_and_access_control(client: AsyncClient, db_session: AsyncSession):
    # 1. Create student owner, faculty guide, and an unrelated student
    owner, owner_headers = await register_and_login(client, role="student", name="Owner Student")
    faculty, faculty_headers = await register_and_login(client, role="faculty", name="Guide Prof")
    unrelated_student, unrel_headers = await register_and_login(client, role="student", name="Other Student")

    created_user_ids = [owner["id"], faculty["id"], unrelated_student["id"]]

    try:
        # 2. Create project by student owner
        proj_payload = {
            "title": "Autonomous Drone Delivery",
            "description": "B.Tech capstone project on drone routing and scheduling.",
            "academic_year": "2025-2026",
            "semester": 8,
            "department": "Computer Science & Engineering",
            "project_type": "capstone",
            "start_date": "2026-01-10",
            "target_deadline": "2026-05-15",
            "faculty_guide_id": faculty["id"],
        }
        create_res = await client.post("/api/v1/projects", json=proj_payload, headers=owner_headers)
        assert create_res.status_code == 201, create_res.text
        project = create_res.json()
        project_id = project["id"]
        assert project["title"] == "Autonomous Drone Delivery"
        assert project["owner"]["id"] == owner["id"]
        assert project["faculty_guide"]["id"] == faculty["id"]

        # Verify owner was automatically added as member with LEADER role
        members_res = await client.get(f"/api/v1/projects/{project_id}/members", headers=owner_headers)
        assert members_res.status_code == 200, members_res.text
        members = members_res.json()
        assert len(members) == 1
        assert members[0]["user_id"] == owner["id"]
        assert members[0]["team_role"] == "leader"

        # 3. Faculty cannot create project (endpoint restricted to get_current_student)
        fac_create_res = await client.post("/api/v1/projects", json=proj_payload, headers=faculty_headers)
        assert fac_create_res.status_code == 403

        # 4. List accessible projects
        # Owner sees it
        owner_list = await client.get("/api/v1/projects", headers=owner_headers)
        assert owner_list.status_code == 200
        assert any(p["id"] == project_id for p in owner_list.json())

        # Faculty sees it because they are assigned as guide
        fac_list = await client.get("/api/v1/projects", headers=faculty_headers)
        assert fac_list.status_code == 200
        assert any(p["id"] == project_id for p in fac_list.json())

        # Unrelated student does NOT see it
        unrel_list = await client.get("/api/v1/projects", headers=unrel_headers)
        assert unrel_list.status_code == 200
        assert not any(p["id"] == project_id for p in unrel_list.json())

        # 5. Access single project details
        # Unrelated student gets 403 Forbidden
        unrel_get = await client.get(f"/api/v1/projects/{project_id}", headers=unrel_headers)
        assert unrel_get.status_code == 403

        # Owner and faculty get 200 OK
        assert (await client.get(f"/api/v1/projects/{project_id}", headers=owner_headers)).status_code == 200
        assert (await client.get(f"/api/v1/projects/{project_id}", headers=faculty_headers)).status_code == 200

        # 6. Add second student as team member
        add_member_res = await client.post(
            f"/api/v1/projects/{project_id}/members",
            json={"user_id": unrelated_student["id"], "team_role": "developer"},
            headers=owner_headers,
        )
        assert add_member_res.status_code == 201, add_member_res.text
        assert add_member_res.json()["user_id"] == unrelated_student["id"]

        # Duplicate member addition rejected
        dup_mem = await client.post(
            f"/api/v1/projects/{project_id}/members",
            json={"user_id": unrelated_student["id"], "team_role": "researcher"},
            headers=owner_headers,
        )
        assert dup_mem.status_code == 400

        # Now newly added member CAN access project
        now_member_get = await client.get(f"/api/v1/projects/{project_id}", headers=unrel_headers)
        assert now_member_get.status_code == 200

        # But newly added member CANNOT update project (only owner can update)
        member_update_try = await client.put(
            f"/api/v1/projects/{project_id}",
            json={"title": "Unauthorized Title Change"},
            headers=unrel_headers,
        )
        assert member_update_try.status_code == 403

        # Owner CAN update project
        owner_update = await client.put(
            f"/api/v1/projects/{project_id}",
            json={"title": "Autonomous Drone Fleet Scheduling"},
            headers=owner_headers,
        )
        assert owner_update.status_code == 200
        assert owner_update.json()["title"] == "Autonomous Drone Fleet Scheduling"

        # 7. Archive project (owner only, preserves records)
        archive_res = await client.post(f"/api/v1/projects/{project_id}/archive", headers=owner_headers)
        assert archive_res.status_code == 200
        assert archive_res.json()["status"] == "archived"

        # Check that records are preserved and readable
        archived_get = await client.get(f"/api/v1/projects/{project_id}", headers=owner_headers)
        assert archived_get.status_code == 200
        assert archived_get.json()["status"] == "archived"

    finally:
        # Cleanup projects first (due to ondelete="RESTRICT" on owner_id), then users
        owner_uids = [uuid.UUID(uid) for uid in created_user_ids]
        await db_session.execute(delete(AcademicProject).where(AcademicProject.owner_id.in_(owner_uids)))
        for uid in created_user_ids:
            await db_session.execute(delete(User).where(User.id == uuid.UUID(uid)))
        await db_session.commit()
