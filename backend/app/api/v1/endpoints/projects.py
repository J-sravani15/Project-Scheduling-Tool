from datetime import date
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, or_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.api.deps import (
    get_current_user,
    get_current_student,
    verify_project_access,
)
from app.models.user import User
from app.models.project import AcademicProject, ProjectMember
from app.models.task import Task, TaskAssignment
from app.models.enums import UserRole, ProjectStatus, TeamRole
from app.schemas.project import (
    AcademicProjectCreate,
    AcademicProjectUpdate,
    AcademicProjectRead,
    FacultyGuideAssignRequest,
)
from app.schemas.member import ProjectMemberCreate, ProjectMemberUpdate, ProjectMemberRead
from app.schemas.user import UserSummary
from app.schemas.workload import TeamWorkloadResponse
from app.schemas.readiness import ReviewReadinessResponse
from app.services.workload_service import WorkloadService
from app.services.readiness_service import ReadinessService

router = APIRouter()


@router.post("", response_model=AcademicProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_in: AcademicProjectCreate,
    current_user: User = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """
    Creates a new academic project with current student as owner.
    Automatically assigns the owner as the project team LEADER.
    """
    # Validate faculty guide if provided
    if project_in.faculty_guide_id:
        fg_query = await db.execute(
            select(User).where(User.id == project_in.faculty_guide_id)
        )
        faculty = fg_query.scalar_one_or_none()
        if not faculty or faculty.role != UserRole.FACULTY:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assigned faculty guide must be an existing user with FACULTY role.",
            )

    project = AcademicProject(
        title=project_in.title,
        description=project_in.description,
        academic_year=project_in.academic_year,
        semester=project_in.semester,
        department=project_in.department,
        project_type=project_in.project_type,
        status=project_in.status,
        start_date=project_in.start_date,
        target_deadline=project_in.target_deadline,
        owner_id=current_user.id,
        faculty_guide_id=project_in.faculty_guide_id,
    )
    db.add(project)
    await db.flush()

    # Add owner as project member with LEADER role
    owner_member = ProjectMember(
        project_id=project.id,
        user_id=current_user.id,
        team_role=TeamRole.LEADER,
    )
    db.add(owner_member)
    await db.commit()

    # Re-fetch with loaded relationships for response schema
    query = await db.execute(
        select(AcademicProject)
        .options(
            selectinload(AcademicProject.owner),
            selectinload(AcademicProject.faculty_guide),
        )
        .where(AcademicProject.id == project.id)
    )
    return query.scalar_one()


@router.get("", response_model=List[AcademicProjectRead])
async def list_accessible_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Lists projects accessible to current user:
    - If Student: projects owned by student OR where student is a registered team member.
    - If Faculty: projects supervised by this faculty guide.
    """
    if current_user.role == UserRole.FACULTY:
        query = (
            select(AcademicProject)
            .options(
                selectinload(AcademicProject.owner),
                selectinload(AcademicProject.faculty_guide),
            )
            .where(AcademicProject.faculty_guide_id == current_user.id)
            .order_by(AcademicProject.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
    else:
        # Student: owned or member
        query = (
            select(AcademicProject)
            .options(
                selectinload(AcademicProject.owner),
                selectinload(AcademicProject.faculty_guide),
            )
            .outerjoin(ProjectMember, ProjectMember.project_id == AcademicProject.id)
            .where(
                or_(
                    AcademicProject.owner_id == current_user.id,
                    ProjectMember.user_id == current_user.id,
                )
            )
            .distinct()
            .order_by(AcademicProject.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/{project_id}", response_model=AcademicProjectRead)
async def get_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves project details for authorized users (owner, member, or guide)."""
    project = await verify_project_access(project_id, current_user, db)
    
    # Reload with user references
    query = await db.execute(
        select(AcademicProject)
        .options(
            selectinload(AcademicProject.owner),
            selectinload(AcademicProject.faculty_guide),
        )
        .where(AcademicProject.id == project.id)
    )
    return query.scalar_one()


@router.put("/{project_id}", response_model=AcademicProjectRead)
async def update_project(
    project_id: UUID,
    project_update: AcademicProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Updates academic project details. Requires project owner privileges."""
    project = await verify_project_access(project_id, current_user, db, require_owner=True)

    if project_update.faculty_guide_id is not None:
        fg_query = await db.execute(
            select(User).where(User.id == project_update.faculty_guide_id)
        )
        faculty = fg_query.scalar_one_or_none()
        if not faculty or faculty.role != UserRole.FACULTY:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assigned faculty guide must be an existing user with FACULTY role.",
            )
        project.faculty_guide_id = project_update.faculty_guide_id

    update_dict = project_update.model_dump(exclude_unset=True)
    update_dict.pop("faculty_guide_id", None)

    for field, value in update_dict.items():
        setattr(project, field, value)

    await db.commit()
    await db.refresh(project)

    # Reload relationships
    query = await db.execute(
        select(AcademicProject)
        .options(
            selectinload(AcademicProject.owner),
            selectinload(AcademicProject.faculty_guide),
        )
        .where(AcademicProject.id == project.id)
    )
    return query.scalar_one()


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Permanently deletes an academic project and associated cascade records.
    Strictly requires project owner privileges.
    """
    project = await verify_project_access(project_id, current_user, db, require_owner=True)
    await db.delete(project)
    await db.commit()
    return None


@router.put("/{project_id}/faculty-guide", response_model=AcademicProjectRead, summary="Assign or change faculty guide")
async def assign_faculty_guide(
    project_id: UUID,
    payload: FacultyGuideAssignRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Assigns or updates the faculty supervisor for an academic project.
    Strictly requires project owner privileges.
    Validates that the selected account exists and has the FACULTY role.
    """
    project = await verify_project_access(project_id, current_user, db, require_owner=True)

    fg_query = await db.execute(
        select(User).where(User.id == payload.faculty_guide_id)
    )
    faculty = fg_query.scalar_one_or_none()
    if not faculty or faculty.role != UserRole.FACULTY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assigned faculty guide must be an existing user with FACULTY role.",
        )

    project.faculty_guide_id = payload.faculty_guide_id
    await db.commit()
    await db.refresh(project)

    query = await db.execute(
        select(AcademicProject)
        .options(
            selectinload(AcademicProject.owner),
            selectinload(AcademicProject.faculty_guide),
        )
        .where(AcademicProject.id == project.id)
    )
    return query.scalar_one()


@router.post("/{project_id}/archive", response_model=AcademicProjectRead)
async def archive_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Archives a project by setting status to ARCHIVED without deleting academic history.
    Requires owner privileges.
    """
    project = await verify_project_access(project_id, current_user, db, require_owner=True)
    project.status = ProjectStatus.ARCHIVED
    await db.commit()
    await db.refresh(project)
    
    query = await db.execute(
        select(AcademicProject)
        .options(
            selectinload(AcademicProject.owner),
            selectinload(AcademicProject.faculty_guide),
        )
        .where(AcademicProject.id == project.id)
    )
    return query.scalar_one()


@router.post("/{project_id}/members", response_model=ProjectMemberRead, status_code=status.HTTP_201_CREATED)
async def add_project_member(
    project_id: UUID,
    member_in: ProjectMemberCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Adds a student team member to the project. Requires owner privileges."""
    project = await verify_project_access(project_id, current_user, db, require_owner=True)

    # Validate target user is a student
    user_query = await db.execute(select(User).where(User.id == member_in.user_id))
    target_user = user_query.scalar_one_or_none()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target user not found.",
        )
    if target_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Faculty members cannot be added as student team members.",
        )

    # Check if target is the project owner
    if target_user.id == project.owner_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The project owner is already the leader of this project.",
        )

    # Check if already a member
    existing_query = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == member_in.user_id,
        )
    )
    if existing_query.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this project.",
        )

    member = ProjectMember(
        project_id=project_id,
        user_id=member_in.user_id,
        team_role=member_in.team_role,
    )
    db.add(member)
    await db.commit()
    await db.refresh(member)

    # Reload with user summary
    q = await db.execute(
        select(ProjectMember)
        .options(selectinload(ProjectMember.user))
        .where(ProjectMember.id == member.id)
    )
    return q.scalar_one()


@router.get("/{project_id}/available-students", response_model=List[UserSummary], summary="List available students for project assignment")
async def list_available_students(
    project_id: UUID,
    search: Optional[str] = Query(None, description="Optional search by name or email"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Lists registered active students who are not yet members of this project and not the project owner.
    Filtered for easy selection in the Add Team Member modal.
    Accessible to users with project access.
    """
    project = await verify_project_access(project_id, current_user, db)

    existing_member_ids_query = select(ProjectMember.user_id).where(ProjectMember.project_id == project_id)

    conditions = [
        User.role == UserRole.STUDENT,
        User.is_active.is_(True),
        User.id != project.owner_id,
        User.id.not_in(existing_member_ids_query),
    ]

    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        conditions.append(
            or_(
                User.full_name.ilike(term),
                User.email.ilike(term),
            )
        )

    query = (
        select(User)
        .where(*conditions)
        .order_by(User.full_name.asc())
        .offset(skip)
        .limit(limit)
    )

    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/{project_id}/members", response_model=List[ProjectMemberRead])
async def list_project_members(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists all team members of the project."""
    await verify_project_access(project_id, current_user, db)
    query = await db.execute(
        select(ProjectMember)
        .options(selectinload(ProjectMember.user))
        .where(ProjectMember.project_id == project_id)
        .order_by(ProjectMember.joined_at)
    )
    return list(query.scalars().all())


@router.put("/{project_id}/members/{user_id}", response_model=ProjectMemberRead)
async def update_project_member_role(
    project_id: UUID,
    user_id: UUID,
    member_update: ProjectMemberUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Updates a project team member's role.
    Requires project owner privileges.
    """
    project = await verify_project_access(project_id, current_user, db, require_owner=True)

    q = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )
    member = q.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project member not found.")

    member.team_role = member_update.team_role
    await db.commit()
    await db.refresh(member)

    res = await db.execute(
        select(ProjectMember)
        .options(selectinload(ProjectMember.user))
        .where(ProjectMember.id == member.id)
    )
    return res.scalar_one()


@router.delete("/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_project_member(
    project_id: UUID,
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Removes a student team member from an academic project.
    Also cleans up any task assignments for this member within the project.
    Requires project owner privileges. The project owner cannot remove themselves.
    """
    project = await verify_project_access(project_id, current_user, db, require_owner=True)

    if user_id == project.owner_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The project owner/leader cannot be removed from the project team.",
        )

    q = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )
    member = q.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project member not found.")

    # Remove any task assignments for this user within this project
    proj_task_ids_q = select(Task.id).where(Task.project_id == project_id)
    await db.execute(
        delete(TaskAssignment).where(
            TaskAssignment.user_id == user_id,
            TaskAssignment.task_id.in_(proj_task_ids_q),
        )
    )

    await db.delete(member)
    await db.commit()
    return None


@router.get("/{project_id}/workload", response_model=TeamWorkloadResponse)
async def get_project_workload(
    project_id: UUID,
    threshold_hours: float = Query(25.0, ge=5.0, le=100.0, description="Semester active capacity threshold"),
    reference_date: Optional[date] = Query(None, description="Evaluation reference date"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Analyzes student team effort allocation, overload alerts, and balance distribution."""
    await verify_project_access(project_id, current_user, db)
    return await WorkloadService.analyze_project_workload(
        project_id=project_id,
        db=db,
        threshold_hours=threshold_hours,
        reference_date=reference_date,
    )


@router.get("/{project_id}/review-readiness", response_model=ReviewReadinessResponse)
async def get_project_review_readiness(
    project_id: UUID,
    reference_date: Optional[date] = Query(None, description="Evaluation reference date"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Evaluates milestone viva readiness, critical path health, and active blockers."""
    await verify_project_access(project_id, current_user, db)
    return await ReadinessService.evaluate_readiness(
        project_id=project_id,
        db=db,
        reference_date=reference_date,
    )
