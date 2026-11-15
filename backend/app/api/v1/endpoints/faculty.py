from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.api.deps import get_current_faculty, get_current_user
from app.models.user import User
from app.models.project import AcademicProject
from app.models.review import ProjectReview
from app.models.enums import ReviewStatus, UserRole
from app.schemas.project import AcademicProjectRead
from app.schemas.review import ProjectReviewCreate, ProjectReviewRead, ProjectReviewUpdate
from app.schemas.user import UserSummary
from app.schemas.workload import TeamWorkloadResponse
from app.schemas.readiness import ReviewReadinessResponse
from app.services.workload_service import WorkloadService
from app.services.readiness_service import ReadinessService
from app.services.notification_service import NotificationService
from pydantic import BaseModel, ConfigDict

router = APIRouter()


class FacultyProjectOverview(BaseModel):
    project: AcademicProjectRead
    workload: TeamWorkloadResponse
    readiness: ReviewReadinessResponse
    reviews: List[ProjectReviewRead]

    model_config = ConfigDict(from_attributes=True)


@router.get("", response_model=List[UserSummary], summary="List registered faculty members")
async def list_faculty_members(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Lists all registered, active faculty members with safe profile fields (ID, name, email).
    Accessible to authenticated students and faculty for supervision assignment.
    """
    query = (
        select(User)
        .where(User.role == UserRole.FACULTY, User.is_active.is_(True))
        .order_by(User.full_name.asc())
    )
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/projects", response_model=List[AcademicProjectRead])
async def list_faculty_supervised_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_faculty: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """
    Lists all academic projects assigned to the current faculty guide.
    Restricted to authenticated faculty users.
    """
    query = (
        select(AcademicProject)
        .options(
            selectinload(AcademicProject.owner),
            selectinload(AcademicProject.faculty_guide),
        )
        .where(AcademicProject.faculty_guide_id == current_faculty.id)
        .order_by(AcademicProject.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/projects/{project_id}/overview", response_model=FacultyProjectOverview)
async def get_faculty_project_overview(
    project_id: UUID,
    current_faculty: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves a comprehensive monitoring dashboard for a supervised project.
    Strictly forbids access if the project is supervised by another faculty guide.
    """
    proj_query = await db.execute(
        select(AcademicProject)
        .options(
            selectinload(AcademicProject.owner),
            selectinload(AcademicProject.faculty_guide),
        )
        .where(AcademicProject.id == project_id)
    )
    project = proj_query.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found.",
        )

    # Strictly enforce that this faculty guide is the supervisor
    if project.faculty_guide_id != current_faculty.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You are not the assigned faculty guide for this project.",
        )

    # Fetch workload and readiness
    workload_data = await WorkloadService.analyze_project_workload(project_id=project_id, db=db)
    readiness_data = await ReadinessService.evaluate_readiness(project_id=project_id, db=db)

    # Fetch reviews
    reviews_query = await db.execute(
        select(ProjectReview)
        .options(selectinload(ProjectReview.faculty))
        .where(ProjectReview.project_id == project_id)
        .order_by(ProjectReview.review_number)
    )
    reviews = list(reviews_query.scalars().all())

    return FacultyProjectOverview(
        project=project,
        workload=workload_data,
        readiness=readiness_data,
        reviews=reviews,
    )


@router.post("/projects/{project_id}/reviews", response_model=ProjectReviewRead, status_code=status.HTTP_201_CREATED)
async def schedule_or_conduct_review(
    project_id: UUID,
    review_in: ProjectReviewCreate,
    current_faculty: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """
    Allows the assigned faculty guide to schedule or score an academic project review.
    """
    proj_query = await db.execute(
        select(AcademicProject).where(AcademicProject.id == project_id)
    )
    project = proj_query.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

    if project.faculty_guide_id != current_faculty.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only the assigned faculty guide can conduct reviews for this project.",
        )

    # Check for duplicate review number
    rev_check = await db.execute(
        select(ProjectReview).where(
            ProjectReview.project_id == project_id,
            ProjectReview.review_number == review_in.review_number,
        )
    )
    if rev_check.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Review number {review_in.review_number} already exists for this project.",
        )

    review = ProjectReview(
        project_id=project_id,
        faculty_id=current_faculty.id,
        review_number=review_in.review_number,
        scheduled_at=review_in.scheduled_at,
        status=review_in.status,
        feedback=review_in.feedback,
        score=review_in.score,
    )
    db.add(review)
    await db.commit()
    await db.refresh(review)

    # Notify all enrolled students when an academic review is scheduled
    if review.status == ReviewStatus.SCHEDULED:
        await NotificationService.notify_review_scheduled(
            db=db,
            review=review,
            project=project,
            faculty=current_faculty,
        )

    q = await db.execute(
        select(ProjectReview)
        .options(selectinload(ProjectReview.faculty))
        .where(ProjectReview.id == review.id)
    )
    return q.scalar_one()


@router.put("/projects/{project_id}/reviews/{review_id}", response_model=ProjectReviewRead)
async def update_or_reschedule_review(
    project_id: UUID,
    review_id: UUID,
    review_update: ProjectReviewUpdate,
    current_faculty: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """
    Allows the assigned faculty guide to reschedule, re-evaluate, or cancel an academic review.
    Triggers student notifications when scheduled_at changes or status becomes cancelled.
    """
    proj_query = await db.execute(
        select(AcademicProject).where(AcademicProject.id == project_id)
    )
    project = proj_query.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

    if project.faculty_guide_id != current_faculty.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only the assigned faculty guide can manage reviews for this project.",
        )

    rev_query = await db.execute(
        select(ProjectReview).where(
            ProjectReview.id == review_id,
            ProjectReview.project_id == project_id,
        )
    )
    review = rev_query.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found.")

    old_scheduled_at = review.scheduled_at
    old_status = review.status

    update_data = review_update.model_dump(exclude_unset=True)

    time_changed = False
    if "scheduled_at" in update_data and update_data["scheduled_at"] is not None:
        if update_data["scheduled_at"] != old_scheduled_at:
            time_changed = True

    status_changed_to_cancelled = False
    if "status" in update_data and update_data["status"] == ReviewStatus.CANCELLED and old_status != ReviewStatus.CANCELLED:
        status_changed_to_cancelled = True

    for field, value in update_data.items():
        setattr(review, field, value)

    await db.commit()
    await db.refresh(review)

    # Notifications
    if status_changed_to_cancelled:
        await NotificationService.notify_review_cancelled(
            db=db,
            review=review,
            project=project,
            faculty=current_faculty,
        )
    elif time_changed and review.status != ReviewStatus.CANCELLED:
        await NotificationService.notify_review_rescheduled(
            db=db,
            review=review,
            project=project,
            faculty=current_faculty,
            previous_scheduled_at=old_scheduled_at,
        )

    q = await db.execute(
        select(ProjectReview)
        .options(selectinload(ProjectReview.faculty))
        .where(ProjectReview.id == review.id)
    )
    return q.scalar_one()


@router.delete("/projects/{project_id}/reviews/{review_id}", response_model=ProjectReviewRead)
async def cancel_review(
    project_id: UUID,
    review_id: UUID,
    current_faculty: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """
    Cancels an academic review and notifies all enrolled students.
    """
    proj_query = await db.execute(
        select(AcademicProject).where(AcademicProject.id == project_id)
    )
    project = proj_query.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

    if project.faculty_guide_id != current_faculty.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only the assigned faculty guide can cancel reviews for this project.",
        )

    rev_query = await db.execute(
        select(ProjectReview).where(
            ProjectReview.id == review_id,
            ProjectReview.project_id == project_id,
        )
    )
    review = rev_query.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found.")

    review.status = ReviewStatus.CANCELLED
    await db.commit()
    await db.refresh(review)

    await NotificationService.notify_review_cancelled(
        db=db,
        review=review,
        project=project,
        faculty=current_faculty,
    )

    q = await db.execute(
        select(ProjectReview)
        .options(selectinload(ProjectReview.faculty))
        .where(ProjectReview.id == review.id)
    )
    return q.scalar_one()


@router.post("/projects/{project_id}/reviews/{review_id}/cancel", response_model=ProjectReviewRead)
async def cancel_review_post(
    project_id: UUID,
    review_id: UUID,
    current_faculty: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """
    POST alias for cancelling an academic review.
    """
    return await cancel_review(project_id, review_id, current_faculty, db)
