import pytest
import pytest_asyncio
import uuid
from datetime import date
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import (
    User,
    AcademicProject,
    ProjectMember,
    Task,
    TaskDependency,
)
from app.models.enums import (
    UserRole,
    ProjectStatus,
    ProjectType,
    TeamRole,
    DependencyType,
)


@pytest.mark.asyncio
async def test_db_unique_email_constraint(db_session: AsyncSession):
    async with db_session.begin():
        unique_email = f"test_{uuid.uuid4().hex[:8]}@college.edu"
        u1 = User(
            full_name="User One",
            email=unique_email,
            password_hash="hashed_pw_1",
            role=UserRole.STUDENT,
        )
        db_session.add(u1)
        await db_session.flush()

        u2 = User(
            full_name="User Two",
            email=unique_email,
            password_hash="hashed_pw_2",
            role=UserRole.STUDENT,
        )
        db_session.add(u2)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    await db_session.rollback()


@pytest.mark.asyncio
async def test_db_unique_project_member_constraint(db_session: AsyncSession):
    async with db_session.begin():
        owner = User(
            full_name="Project Lead",
            email=f"lead_{uuid.uuid4().hex[:8]}@college.edu",
            password_hash="hashed_pw",
            role=UserRole.STUDENT,
        )
        member = User(
            full_name="Project Member",
            email=f"member_{uuid.uuid4().hex[:8]}@college.edu",
            password_hash="hashed_pw",
            role=UserRole.STUDENT,
        )
        db_session.add_all([owner, member])
        await db_session.flush()

        proj = AcademicProject(
            title="Scheduling Platform",
            academic_year="2025-2026",
            semester=8,
            department="CSE",
            project_type=ProjectType.CAPSTONE,
            status=ProjectStatus.PLANNING,
            start_date=date(2026, 1, 1),
            target_deadline=date(2026, 5, 1),
            owner_id=owner.id,
        )
        db_session.add(proj)
        await db_session.flush()

        pm1 = ProjectMember(
            project_id=proj.id,
            user_id=member.id,
            team_role=TeamRole.DEVELOPER,
        )
        db_session.add(pm1)
        await db_session.flush()

        # Duplicate (project_id, user_id)
        pm2 = ProjectMember(
            project_id=proj.id,
            user_id=member.id,
            team_role=TeamRole.TESTER,
        )
        db_session.add(pm2)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    await db_session.rollback()


@pytest.mark.asyncio
async def test_db_self_dependency_constraint(db_session: AsyncSession):
    async with db_session.begin():
        owner = User(
            full_name="Owner",
            email=f"owner_{uuid.uuid4().hex[:8]}@college.edu",
            password_hash="hashed_pw",
            role=UserRole.STUDENT,
        )
        db_session.add(owner)
        await db_session.flush()

        proj = AcademicProject(
            title="Dependency Test Project",
            academic_year="2025-2026",
            semester=8,
            department="CSE",
            start_date=date(2026, 1, 1),
            target_deadline=date(2026, 5, 1),
            owner_id=owner.id,
        )
        db_session.add(proj)
        await db_session.flush()

        task = Task(
            project_id=proj.id,
            title="Single Task",
            due_date=date(2026, 2, 1),
            estimated_duration_hours=10.0,
        )
        db_session.add(task)
        await db_session.flush()

        # Self-dependency constraint check
        dep = TaskDependency(
            task_id=task.id,
            depends_on_task_id=task.id,
            dependency_type=DependencyType.FINISH_TO_START,
        )
        db_session.add(dep)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    await db_session.rollback()


@pytest.mark.asyncio
async def test_db_project_date_range_check_constraint(db_session: AsyncSession):
    async with db_session.begin():
        owner = User(
            full_name="Owner",
            email=f"owner_{uuid.uuid4().hex[:8]}@college.edu",
            password_hash="hashed_pw",
            role=UserRole.STUDENT,
        )
        db_session.add(owner)
        await db_session.flush()

        # Check constraint: target_deadline < start_date
        proj = AcademicProject(
            title="Invalid Date Project",
            academic_year="2025-2026",
            semester=8,
            department="CSE",
            start_date=date(2026, 5, 1),
            target_deadline=date(2026, 1, 1),
            owner_id=owner.id,
        )
        db_session.add(proj)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    await db_session.rollback()
