from datetime import datetime, timezone
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user, verify_project_access
from app.models.user import User
from app.models.milestone import AcademicMilestone
from app.models.enums import MilestoneStatus
from app.schemas.milestone import (
    AcademicMilestoneCreate,
    AcademicMilestoneUpdate,
    AcademicMilestoneRead,
)

router = APIRouter()


@router.post("/projects/{project_id}/milestones", response_model=AcademicMilestoneRead, status_code=status.HTTP_201_CREATED)
async def create_milestone(
    project_id: UUID,
    milestone_in: AcademicMilestoneCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Creates a new academic milestone for the project."""
    await verify_project_access(project_id, current_user, db, require_write=True)

    # Check for duplicate sequence number in project
    seq_query = await db.execute(
        select(AcademicMilestone).where(
            AcademicMilestone.project_id == project_id,
            AcademicMilestone.sequence_number == milestone_in.sequence_number,
        )
    )
    if seq_query.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Milestone with sequence number {milestone_in.sequence_number} already exists in this project.",
        )

    milestone = AcademicMilestone(
        project_id=project_id,
        title=milestone_in.title,
        description=milestone_in.description,
        milestone_type=milestone_in.milestone_type,
        sequence_number=milestone_in.sequence_number,
        planned_date=milestone_in.planned_date,
        status=milestone_in.status,
        is_required=milestone_in.is_required,
    )
    db.add(milestone)
    await db.commit()
    await db.refresh(milestone)
    return milestone


@router.get("/projects/{project_id}/milestones", response_model=List[AcademicMilestoneRead])
async def list_project_milestones(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists all academic milestones of a project ordered by sequence number."""
    await verify_project_access(project_id, current_user, db)
    query = await db.execute(
        select(AcademicMilestone)
        .where(AcademicMilestone.project_id == project_id)
        .order_by(AcademicMilestone.sequence_number)
    )
    return list(query.scalars().all())


@router.put("/milestones/{milestone_id}", response_model=AcademicMilestoneRead)
async def update_milestone(
    milestone_id: UUID,
    milestone_update: AcademicMilestoneUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Updates an academic milestone."""
    query = await db.execute(
        select(AcademicMilestone).where(AcademicMilestone.id == milestone_id)
    )
    milestone = query.scalar_one_or_none()
    if not milestone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Milestone not found.")

    await verify_project_access(milestone.project_id, current_user, db, require_write=True)

    update_dict = milestone_update.model_dump(exclude_unset=True)

    # Validate sequence number uniqueness if updated
    if "sequence_number" in update_dict and update_dict["sequence_number"] != milestone.sequence_number:
        seq_check = await db.execute(
            select(AcademicMilestone).where(
                AcademicMilestone.project_id == milestone.project_id,
                AcademicMilestone.sequence_number == update_dict["sequence_number"],
                AcademicMilestone.id != milestone.id,
            )
        )
        if seq_check.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Milestone with sequence number {update_dict['sequence_number']} already exists in this project.",
            )

    if "status" in update_dict:
        status_val = update_dict["status"]
        is_completed = (
            status_val == MilestoneStatus.COMPLETED
            or str(status_val).lower() == "completed"
        )
        if is_completed:
            if not milestone.completed_at:
                milestone.completed_at = datetime.now(timezone.utc)
        else:
            milestone.completed_at = None

    for field, value in update_dict.items():
        setattr(milestone, field, value)

    await db.commit()
    await db.refresh(milestone)
    return milestone


@router.delete("/milestones/{milestone_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_milestone(
    milestone_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Deletes an academic milestone. Associated tasks have milestone_id automatically set to NULL.
    Requires write access to the project.
    """
    query = await db.execute(
        select(AcademicMilestone).where(AcademicMilestone.id == milestone_id)
    )
    milestone = query.scalar_one_or_none()
    if not milestone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Milestone not found.")

    await verify_project_access(milestone.project_id, current_user, db, require_write=True)

    await db.delete(milestone)
    await db.commit()
    return None


@router.patch("/milestones/{milestone_id}/status", response_model=AcademicMilestoneRead)
async def update_milestone_status(
    milestone_id: UUID,
    status_value: MilestoneStatus,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Updates status of a milestone (sets completed_at when status becomes COMPLETED)."""
    query = await db.execute(
        select(AcademicMilestone).where(AcademicMilestone.id == milestone_id)
    )
    milestone = query.scalar_one_or_none()
    if not milestone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Milestone not found.")

    await verify_project_access(milestone.project_id, current_user, db, require_write=True)

    is_completed = (
        status_value == MilestoneStatus.COMPLETED
        or str(status_value).lower() == "completed"
    )
    milestone.status = status_value
    if is_completed:
        if not milestone.completed_at:
            milestone.completed_at = datetime.now(timezone.utc)
    else:
        milestone.completed_at = None

    await db.commit()
    await db.refresh(milestone)
    return milestone
