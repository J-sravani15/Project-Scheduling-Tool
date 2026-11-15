import pytest
import uuid
from datetime import date
from httpx import AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import User, AcademicProject, Task, TaskDependency
from app.models.enums import UserRole, ProjectStatus, TaskStatus, TaskPriority, DependencyType


@pytest.fixture
def project_setup_data():
    """Generates unique email."""
    return {
        "user_email": f"lead_{uuid.uuid4().hex[:8]}@college.edu",
    }


@pytest.mark.asyncio
async def test_api_cpm_nonexistent_project(client: AsyncClient):
    fake_id = uuid.uuid4()
    resp = await client.get(f"/api/v1/projects/{fake_id}/schedule/cpm")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_api_scheduling_full_flow(client: AsyncClient, db_session: AsyncSession, project_setup_data):
    """
    Creates an academic project with 3 tasks:
      T1 (4h) -> T2 (6h) -> T3 (10h)
    Tests CPM, Priority Scheduling, and PERT endpoints end-to-end.
    Cleans up all created test records at the end.
    """
    user = User(
        full_name="Scheduler Tester",
        email=project_setup_data["user_email"],
        password_hash="fake_hash",
        role=UserRole.STUDENT,
    )
    db_session.add(user)
    await db_session.flush()

    proj = AcademicProject(
        title="Capstone Scheduling Test Project",
        academic_year="2025-2026",
        semester=8,
        department="CSE",
        status=ProjectStatus.IN_PROGRESS,
        start_date=date(2026, 1, 1),
        target_deadline=date(2026, 6, 1),
        owner_id=user.id,
    )
    db_session.add(proj)
    await db_session.flush()

    # Task 1 (Prereq)
    t1 = Task(
        project_id=proj.id,
        title="Literature Survey",
        status=TaskStatus.COMPLETED,
        priority=TaskPriority.HIGH,
        estimated_duration_hours=4.0,
        due_date=date(2026, 1, 15),
    )
    # Task 2 (Dependent on T1)
    t2 = Task(
        project_id=proj.id,
        title="System Architecture",
        status=TaskStatus.TODO,
        priority=TaskPriority.CRITICAL,
        estimated_duration_hours=6.0,
        due_date=date(2026, 2, 1),
    )
    # Task 3 (Dependent on T2)
    t3 = Task(
        project_id=proj.id,
        title="Prototype Implementation",
        status=TaskStatus.TODO,
        priority=TaskPriority.MEDIUM,
        estimated_duration_hours=10.0,
        due_date=date(2026, 3, 1),
    )
    db_session.add_all([t1, t2, t3])
    await db_session.flush()

    # Dependencies: T1 -> T2 -> T3
    dep1 = TaskDependency(task_id=t2.id, depends_on_task_id=t1.id, dependency_type=DependencyType.FINISH_TO_START)
    dep2 = TaskDependency(task_id=t3.id, depends_on_task_id=t2.id, dependency_type=DependencyType.FINISH_TO_START)
    db_session.add_all([dep1, dep2])
    await db_session.commit()

    proj_id = proj.id
    t1_id, t2_id, t3_id = t1.id, t2.id, t3.id

    try:
        # 1. Test CPM Endpoint
        cpm_resp = await client.get(f"/api/v1/projects/{proj_id}/schedule/cpm")
        assert cpm_resp.status_code == 200
        cpm_data = cpm_resp.json()
        assert cpm_data["total_project_duration_hours"] == 20.0  # 4 + 6 + 10 = 20
        assert len(cpm_data["critical_tasks"]) == 3
        assert str(t1_id) in cpm_data["tasks"]
        assert cpm_data["tasks"][str(t1_id)]["early_finish"] == 4.0
        assert cpm_data["tasks"][str(t2_id)]["early_finish"] == 10.0
        assert cpm_data["tasks"][str(t3_id)]["early_finish"] == 20.0

        # 2. Test Priority Scheduling Endpoint
        prio_resp = await client.get(f"/api/v1/projects/{proj_id}/schedule/priority")
        assert prio_resp.status_code == 200
        prio_data = prio_resp.json()
        
        # T1 is COMPLETED -> in completed_tasks
        # T2's prereq T1 is COMPLETED -> T2 is eligible -> in recommended_tasks
        # T3's prereq T2 is TODO -> T3 is blocked -> in blocked_tasks
        completed_ids = [t["id"] for t in prio_data["completed_tasks"]]
        recommended_ids = [t["id"] for t in prio_data["recommended_tasks"]]
        blocked_ids = [t["id"] for t in prio_data["blocked_tasks"]]

        assert str(t1_id) in completed_ids
        assert str(t2_id) in recommended_ids
        assert str(t3_id) in blocked_ids

        # 3. Test PERT Analysis Endpoint
        pert_payload = {
            "target_deadline_hours": 24.0,
            "estimates": [
                {"task_id": str(t1_id), "optimistic_hours": 3.0, "most_likely_hours": 4.0, "pessimistic_hours": 5.0},
                {"task_id": str(t2_id), "optimistic_hours": 4.0, "most_likely_hours": 6.0, "pessimistic_hours": 8.0},
                {"task_id": str(t3_id), "optimistic_hours": 8.0, "most_likely_hours": 10.0, "pessimistic_hours": 12.0},
            ]
        }
        pert_resp = await client.post(f"/api/v1/projects/{proj_id}/schedule/pert", json=pert_payload)
        assert pert_resp.status_code == 200
        pert_data = pert_resp.json()
        assert pert_data["critical_path_expected_duration_hours"] == 20.0
        assert pert_data["probability_of_meeting_deadline"] is not None
        assert pert_data["probability_of_meeting_deadline"] > 0.95  # 24h target vs 20h expected
        assert len(pert_data["assumptions"]) > 0

    finally:
        # Clean up test project and user to preserve pristine DB
        await db_session.execute(delete(AcademicProject).where(AcademicProject.id == proj_id))
        await db_session.execute(delete(User).where(User.id == user.id))
        await db_session.commit()


@pytest.mark.asyncio
async def test_api_scheduling_rbac_and_authorization(client: AsyncClient, db_session: AsyncSession):
    """
    Verifies that scheduling endpoints enforce RBAC project access:
    - Project owner receives 200 OK.
    - Non-member / unrelated student receives 403 Forbidden.
    - Nonexistent project returns 404 Not Found.
    """
    # 1. Register owner and unrelated student
    owner_email = f"owner_{uuid.uuid4().hex[:8]}@college.edu"
    unrel_email = f"unrel_{uuid.uuid4().hex[:8]}@college.edu"
    pwd = "TestPassword2026!"

    res1 = await client.post("/api/v1/auth/register", json={"email": owner_email, "password": pwd, "full_name": "Project Owner", "role": "student"})
    assert res1.status_code == 201
    owner_id = res1.json()["id"]

    res2 = await client.post("/api/v1/auth/register", json={"email": unrel_email, "password": pwd, "full_name": "Unrelated Student", "role": "student"})
    assert res2.status_code == 201
    unrel_id = res2.json()["id"]

    t1_resp = await client.post("/api/v1/auth/login/json", json={"email": owner_email, "password": pwd})
    owner_token = t1_resp.json()["access_token"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    t2_resp = await client.post("/api/v1/auth/login/json", json={"email": unrel_email, "password": pwd})
    unrel_token = t2_resp.json()["access_token"]
    unrel_headers = {"Authorization": f"Bearer {unrel_token}"}

    # 2. Create project under owner
    proj_resp = await client.post(
        "/api/v1/projects",
        headers=owner_headers,
        json={
            "title": "RBAC Scheduling Test Project",
            "academic_year": "2025-2026",
            "semester": 8,
            "department": "CSE",
            "start_date": "2026-01-01",
            "target_deadline": "2026-06-01",
        },
    )
    assert proj_resp.status_code == 201
    proj_id = proj_resp.json()["id"]

    # Add a task
    task_resp = await client.post(
        f"/api/v1/projects/{proj_id}/tasks",
        headers=owner_headers,
        json={
            "title": "Initial Setup",
            "priority": "high",
            "estimated_duration_hours": 8.0,
            "due_date": "2026-02-01",
        },
    )
    assert task_resp.status_code == 201
    task_id = task_resp.json()["id"]

    pert_payload = {
        "target_deadline_hours": 10.0,
        "estimates": [
            {"task_id": task_id, "optimistic_hours": 6.0, "most_likely_hours": 8.0, "pessimistic_hours": 12.0}
        ],
    }

    try:
        # A. Owner access: 200 OK
        cpm_ok = await client.get(f"/api/v1/projects/{proj_id}/schedule/cpm", headers=owner_headers)
        assert cpm_ok.status_code == 200

        prio_ok = await client.get(f"/api/v1/projects/{proj_id}/schedule/priority", headers=owner_headers)
        assert prio_ok.status_code == 200

        pert_ok = await client.post(f"/api/v1/projects/{proj_id}/schedule/pert", headers=owner_headers, json=pert_payload)
        assert pert_ok.status_code == 200

        # B. Unrelated user access: 403 Forbidden
        cpm_forbidden = await client.get(f"/api/v1/projects/{proj_id}/schedule/cpm", headers=unrel_headers)
        assert cpm_forbidden.status_code == 403
        assert "do not have permission" in cpm_forbidden.json()["detail"].lower()

        prio_forbidden = await client.get(f"/api/v1/projects/{proj_id}/schedule/priority", headers=unrel_headers)
        assert prio_forbidden.status_code == 403
        assert "do not have permission" in prio_forbidden.json()["detail"].lower()

        pert_forbidden = await client.post(f"/api/v1/projects/{proj_id}/schedule/pert", headers=unrel_headers, json=pert_payload)
        assert pert_forbidden.status_code == 403
        assert "do not have permission" in pert_forbidden.json()["detail"].lower()

    finally:
        # Clean up database records
        await db_session.execute(delete(AcademicProject).where(AcademicProject.id == uuid.UUID(proj_id)))
        await db_session.execute(delete(User).where(User.id.in_([uuid.UUID(owner_id), uuid.UUID(unrel_id)])))
        await db_session.commit()


@pytest.mark.asyncio
async def test_api_cpm_parallel_tasks_and_shared_successor(client: AsyncClient, db_session: AsyncSession):
    """
    Tests end-to-end CPM API calculation with the intended parallel structure:
      1. Requirement Analysis (4h) -> System Design (6h)
      2. System Design -> Backend Implementation (10h)
      3. System Design -> Frontend Implementation (8h)  [Non-critical with 2h slack]
      4. Backend & Frontend -> Integration Testing (4h)  [Shared successor]
      5. Integration Testing -> Documentation (5h)
    
    Verifies:
      - Total duration = 29.0h (4 + 6 + 10 + 4 + 5)
      - Integration Testing Early Start = max(20.0, 18.0) = 20.0h
      - Frontend Implementation has slack = 2.0h and is_critical = False
      - Backend Implementation has slack = 0.0h and is_critical = True
      - Exactly 5 critical tasks out of 6
    """
    user_email = f"lead_{uuid.uuid4().hex[:8]}@college.edu"
    user = User(
        full_name="Parallel Scheduler Tester",
        email=user_email,
        password_hash="fake_hash",
        role=UserRole.STUDENT,
    )
    db_session.add(user)
    await db_session.flush()

    proj = AcademicProject(
        title="Parallel Capstone Test Project",
        academic_year="2025-2026",
        semester=8,
        department="CSE",
        status=ProjectStatus.IN_PROGRESS,
        start_date=date(2026, 1, 1),
        target_deadline=date(2026, 6, 1),
        owner_id=user.id,
    )
    db_session.add(proj)
    await db_session.flush()

    # Tasks
    t1 = Task(project_id=proj.id, title="Requirement Analysis", status=TaskStatus.TODO, priority=TaskPriority.HIGH, estimated_duration_hours=4.0, due_date=date(2026, 2, 1))
    t2 = Task(project_id=proj.id, title="System Design", status=TaskStatus.TODO, priority=TaskPriority.HIGH, estimated_duration_hours=6.0, due_date=date(2026, 2, 15))
    t3 = Task(project_id=proj.id, title="Backend Implementation", status=TaskStatus.TODO, priority=TaskPriority.CRITICAL, estimated_duration_hours=10.0, due_date=date(2026, 3, 1))
    t4 = Task(project_id=proj.id, title="Frontend Implementation", status=TaskStatus.TODO, priority=TaskPriority.HIGH, estimated_duration_hours=8.0, due_date=date(2026, 3, 1))
    t5 = Task(project_id=proj.id, title="Integration Testing", status=TaskStatus.TODO, priority=TaskPriority.HIGH, estimated_duration_hours=4.0, due_date=date(2026, 3, 15))
    t6 = Task(project_id=proj.id, title="Documentation", status=TaskStatus.TODO, priority=TaskPriority.MEDIUM, estimated_duration_hours=5.0, due_date=date(2026, 4, 1))
    db_session.add_all([t1, t2, t3, t4, t5, t6])
    await db_session.flush()

    # Intended dependencies (6 dependency edges, no erroneous Backend -> Frontend edge)
    deps = [
        TaskDependency(task_id=t2.id, depends_on_task_id=t1.id),
        TaskDependency(task_id=t3.id, depends_on_task_id=t2.id),
        TaskDependency(task_id=t4.id, depends_on_task_id=t2.id),
        TaskDependency(task_id=t5.id, depends_on_task_id=t3.id),
        TaskDependency(task_id=t5.id, depends_on_task_id=t4.id),
        TaskDependency(task_id=t6.id, depends_on_task_id=t5.id),
    ]
    db_session.add_all(deps)
    await db_session.commit()

    proj_id = proj.id
    t1_id, t2_id, t3_id, t4_id, t5_id, t6_id = t1.id, t2.id, t3.id, t4.id, t5.id, t6.id

    try:
        resp = await client.get(f"/api/v1/projects/{proj_id}/schedule/cpm")
        assert resp.status_code == 200
        data = resp.json()

        assert data["total_project_duration_hours"] == 29.0
        assert len(data["critical_tasks"]) == 5
        assert str(t4_id) not in [str(ct) for ct in data["critical_tasks"]]

        tasks_resp = data["tasks"]
        # Req Analysis
        assert tasks_resp[str(t1_id)]["early_start"] == 0.0
        assert tasks_resp[str(t1_id)]["early_finish"] == 4.0
        assert tasks_resp[str(t1_id)]["is_critical"] is True

        # System Design
        assert tasks_resp[str(t2_id)]["early_start"] == 4.0
        assert tasks_resp[str(t2_id)]["early_finish"] == 10.0
        assert tasks_resp[str(t2_id)]["is_critical"] is True

        # Parallel Backend
        assert tasks_resp[str(t3_id)]["early_start"] == 10.0
        assert tasks_resp[str(t3_id)]["early_finish"] == 20.0
        assert tasks_resp[str(t3_id)]["slack"] == 0.0
        assert tasks_resp[str(t3_id)]["is_critical"] is True

        # Parallel Frontend (shorter branch: 8h duration)
        assert tasks_resp[str(t4_id)]["early_start"] == 10.0
        assert tasks_resp[str(t4_id)]["early_finish"] == 18.0
        assert tasks_resp[str(t4_id)]["late_start"] == 12.0
        assert tasks_resp[str(t4_id)]["late_finish"] == 20.0
        assert tasks_resp[str(t4_id)]["slack"] == 2.0
        assert tasks_resp[str(t4_id)]["is_critical"] is False

        # Shared Successor: Integration Testing waits for both
        assert tasks_resp[str(t5_id)]["early_start"] == 20.0
        assert tasks_resp[str(t5_id)]["early_finish"] == 24.0
        assert tasks_resp[str(t5_id)]["is_critical"] is True

        # Documentation
        assert tasks_resp[str(t6_id)]["early_start"] == 24.0
        assert tasks_resp[str(t6_id)]["early_finish"] == 29.0
        assert tasks_resp[str(t6_id)]["is_critical"] is True

    finally:
        await db_session.execute(delete(AcademicProject).where(AcademicProject.id == proj_id))
        await db_session.execute(delete(User).where(User.id == user.id))
        await db_session.commit()

