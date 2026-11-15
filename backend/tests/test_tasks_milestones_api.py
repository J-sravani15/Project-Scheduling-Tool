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
async def test_milestone_and_task_management_flow(client: AsyncClient, db_session: AsyncSession):
    # Setup owner, teammate student, and outsider student
    owner, owner_headers = await register_and_login(client, role="student", name="Leader Student")
    teammate, tm_headers = await register_and_login(client, role="student", name="Teammate Student")
    outsider, out_headers = await register_and_login(client, role="student", name="Outsider Student")

    created_users = [owner["id"], teammate["id"], outsider["id"]]

    try:
        # Create Project
        proj_payload = {
            "title": "Smart Campus Energy Grid",
            "academic_year": "2025-2026",
            "semester": 8,
            "department": "Electrical & Electronics Engineering",
            "project_type": "capstone",
            "start_date": "2026-01-15",
            "target_deadline": "2026-05-30",
        }
        p_res = await client.post("/api/v1/projects", json=proj_payload, headers=owner_headers)
        assert p_res.status_code == 201, p_res.text
        project_id = p_res.json()["id"]

        # Add teammate to project
        mem_res = await client.post(
            f"/api/v1/projects/{project_id}/members",
            json={"user_id": teammate["id"], "team_role": "developer"},
            headers=owner_headers,
        )
        assert mem_res.status_code == 201

        # ==========================================
        # 1. MILESTONE MANAGEMENT
        # ==========================================
        m1_payload = {
            "title": "System Architecture Design",
            "description": "Design hardware interfaces and microgrid simulator",
            "milestone_type": "system_design",
            "sequence_number": 1,
            "planned_date": "2026-02-28",
            "status": "pending",
            "is_required": True,
        }
        m1_res = await client.post(f"/api/v1/projects/{project_id}/milestones", json=m1_payload, headers=owner_headers)
        assert m1_res.status_code == 201, m1_res.text
        m1 = m1_res.json()
        m1_id = m1["id"]

        # Duplicate sequence number rejected
        dup_m = await client.post(f"/api/v1/projects/{project_id}/milestones", json=m1_payload, headers=owner_headers)
        assert dup_m.status_code == 400

        # Milestone 2
        m2_payload = {
            "title": "Hardware Implementation",
            "milestone_type": "implementation",
            "sequence_number": 2,
            "planned_date": "2026-04-15",
            "status": "pending",
            "is_required": True,
        }
        m2_res = await client.post(f"/api/v1/projects/{project_id}/milestones", json=m2_payload, headers=owner_headers)
        assert m2_res.status_code == 201
        m2_id = m2_res.json()["id"]

        # List milestones (ordered by sequence)
        list_m = await client.get(f"/api/v1/projects/{project_id}/milestones", headers=owner_headers)
        assert list_m.status_code == 200
        milestones = list_m.json()
        assert len(milestones) == 2
        assert milestones[0]["sequence_number"] == 1
        assert milestones[1]["sequence_number"] == 2

        # Update milestone & patch status
        patch_m = await client.patch(f"/api/v1/milestones/{m1_id}/status?status_value=completed", headers=owner_headers)
        assert patch_m.status_code == 200
        assert patch_m.json()["status"] == "completed"
        assert patch_m.json()["completed_at"] is not None

        # Reset status clears completed_at
        patch_reset = await client.patch(f"/api/v1/milestones/{m1_id}/status?status_value=in_progress", headers=owner_headers)
        assert patch_reset.status_code == 200
        assert patch_reset.json()["status"] == "in_progress"
        assert patch_reset.json()["completed_at"] is None

        # ==========================================
        # 2. TASK CREATION & FILTERING
        # ==========================================
        t1_payload = {
            "title": "Circuit Simulation",
            "milestone_id": m1_id,
            "status": "in_progress",
            "priority": "high",
            "estimated_duration_hours": 20.0,
            "start_date": "2026-01-20",
            "due_date": "2026-02-15",
        }
        t1_res = await client.post(f"/api/v1/projects/{project_id}/tasks", json=t1_payload, headers=owner_headers)
        assert t1_res.status_code == 201, t1_res.text
        t1 = t1_res.json()
        t1_id = t1["id"]

        t2_payload = {
            "title": "PCB Fabrication",
            "milestone_id": m2_id,
            "status": "todo",
            "priority": "critical",
            "estimated_duration_hours": 30.0,
            "start_date": "2026-02-16",
            "due_date": "2026-03-20",
        }
        t2_res = await client.post(f"/api/v1/projects/{project_id}/tasks", json=t2_payload, headers=tm_headers)
        assert t2_res.status_code == 201
        t2_id = t2_res.json()["id"]

        # Outsider cannot create task (403 Forbidden)
        out_task = await client.post(f"/api/v1/projects/{project_id}/tasks", json=t2_payload, headers=out_headers)
        assert out_task.status_code == 403

        # Task filtering by priority
        filter_crit = await client.get(f"/api/v1/projects/{project_id}/tasks?priority=critical", headers=owner_headers)
        assert filter_crit.status_code == 200
        crit_tasks = filter_crit.json()
        assert len(crit_tasks) == 1
        assert crit_tasks[0]["id"] == t2_id

        # Update task status to completed
        patch_t1 = await client.patch(f"/api/v1/tasks/{t1_id}/status?status_value=completed", headers=owner_headers)
        assert patch_t1.status_code == 200
        assert patch_t1.json()["status"] == "completed"
        assert patch_t1.json()["completed_at"] is not None

        # ==========================================
        # 3. TASK ASSIGNMENTS
        # ==========================================
        # Assign teammate to task 2
        assign_res = await client.post(
            f"/api/v1/tasks/{t2_id}/assignments",
            json={"user_id": teammate["id"]},
            headers=owner_headers,
        )
        assert assign_res.status_code == 201, assign_res.text
        assert assign_res.json()["user_id"] == teammate["id"]

        # Duplicate assignment rejected
        dup_assign = await client.post(
            f"/api/v1/tasks/{t2_id}/assignments",
            json={"user_id": teammate["id"]},
            headers=owner_headers,
        )
        assert dup_assign.status_code == 400

        # Cannot assign outsider (not a team member)
        out_assign = await client.post(
            f"/api/v1/tasks/{t2_id}/assignments",
            json={"user_id": outsider["id"]},
            headers=owner_headers,
        )
        assert out_assign.status_code == 400
        assert "not a registered member" in out_assign.json()["detail"].lower()

        # Filter tasks by assigned user
        assigned_filter = await client.get(f"/api/v1/projects/{project_id}/tasks?assigned_user_id={teammate['id']}", headers=owner_headers)
        assert assigned_filter.status_code == 200
        assert len(assigned_filter.json()) == 1
        assert assigned_filter.json()[0]["id"] == t2_id

        # Unassign teammate
        unassign_res = await client.delete(f"/api/v1/tasks/{t2_id}/assignments/{teammate['id']}", headers=owner_headers)
        assert unassign_res.status_code == 204

        # Re-assign teammate for later workload checks
        await client.post(
            f"/api/v1/tasks/{t2_id}/assignments",
            json={"user_id": teammate["id"]},
            headers=owner_headers,
        )

        # Also assign owner to task 2 (verifying multiple concurrent assignees on a single task)
        assign_owner_res = await client.post(
            f"/api/v1/tasks/{t2_id}/assignments",
            json={"user_id": owner["id"]},
            headers=owner_headers,
        )
        assert assign_owner_res.status_code == 201

        # Check GET /tasks/{t2_id}/assignments returns both assignees
        get_assigns = await client.get(f"/api/v1/tasks/{t2_id}/assignments", headers=owner_headers)
        assert get_assigns.status_code == 200
        assign_list = get_assigns.json()
        assert len(assign_list) == 2
        assignee_ids = {a["user_id"] for a in assign_list}
        assert teammate["id"] in assignee_ids
        assert owner["id"] in assignee_ids

        # Check GET /projects/{project_id}/tasks returns eager-loaded assignments with user details
        list_tasks_res = await client.get(f"/api/v1/projects/{project_id}/tasks", headers=owner_headers)
        assert list_tasks_res.status_code == 200
        tasks_retrieved = list_tasks_res.json()
        t2_item = next(t for t in tasks_retrieved if t["id"] == t2_id)
        assert len(t2_item["assignments"]) == 2
        assert t2_item["assignments"][0]["user"]["full_name"] is not None

        # Clean up owner assignment so downstream tests maintain expected single-assignee state
        del_owner_assign = await client.delete(f"/api/v1/tasks/{t2_id}/assignments/{owner['id']}", headers=owner_headers)
        assert del_owner_assign.status_code == 204

        # ==========================================
        # 4. TASK DEPENDENCIES & CYCLE DETECTION
        # ==========================================
        # Task 2 depends on Task 1
        dep_payload = {
            "depends_on_task_id": t1_id,
            "dependency_type": "finish_to_start",
        }
        dep_res = await client.post(f"/api/v1/tasks/{t2_id}/dependencies", json=dep_payload, headers=owner_headers)
        assert dep_res.status_code == 201, dep_res.text
        assert dep_res.json()["task_id"] == t2_id
        assert dep_res.json()["depends_on_task_id"] == t1_id

        # Self-dependency rejected
        self_dep = await client.post(
            f"/api/v1/tasks/{t1_id}/dependencies",
            json={"depends_on_task_id": t1_id, "dependency_type": "finish_to_start"},
            headers=owner_headers,
        )
        assert self_dep.status_code == 400
        assert "self-dependency" in self_dep.json()["detail"].lower()

        # Duplicate dependency rejected
        dup_dep = await client.post(f"/api/v1/tasks/{t2_id}/dependencies", json=dep_payload, headers=owner_headers)
        assert dup_dep.status_code == 400

        # Cycle Detection: Trying to add Task 1 depends on Task 2 (t1 -> t2 -> t1)
        cycle_payload = {
            "depends_on_task_id": t2_id,
            "dependency_type": "finish_to_start",
        }
        cycle_res = await client.post(f"/api/v1/tasks/{t1_id}/dependencies", json=cycle_payload, headers=owner_headers)
        assert cycle_res.status_code == 422, cycle_res.text
        assert "cycle detected" in cycle_res.json()["detail"].lower()

        # Remove dependency edge
        del_dep = await client.delete(f"/api/v1/tasks/{t2_id}/dependencies/{t1_id}", headers=owner_headers)
        assert del_dep.status_code == 204

    finally:
        owner_uids = [uuid.UUID(uid) for uid in created_users]
        await db_session.execute(delete(AcademicProject).where(AcademicProject.owner_id.in_(owner_uids)))
        for uid in created_users:
            await db_session.execute(delete(User).where(User.id == uuid.UUID(uid)))
        await db_session.commit()
