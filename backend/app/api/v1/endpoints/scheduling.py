from datetime import date
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user_optional, verify_project_access
from app.models.user import User
from app.services.scheduling_service import SchedulingService
from app.schemas.scheduling import (
    CpmAnalysisResponse,
    PriorityScheduleResponse,
    PertCalculationRequest,
    PertAnalysisResponse,
)

router = APIRouter()


@router.get(
    "/{project_id}/schedule/cpm",
    response_model=CpmAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Compute Critical Path Method (CPM) Schedule",
    description="Calculates Early Start (ES), Early Finish (EF), Late Start (LS), Late Finish (LF), "
                "total float (slack), and identifies all critical tasks and paths for the project.",
)
async def get_project_cpm(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    if current_user:
        await verify_project_access(project_id=project_id, current_user=current_user, db=db)
    return await SchedulingService.calculate_project_cpm(project_id=project_id, db=db)


@router.get(
    "/{project_id}/schedule/priority",
    response_model=PriorityScheduleResponse,
    status_code=status.HTTP_200_OK,
    summary="Compute Priority Task Recommendations",
    description="Ranks tasks using a multi-factor priority algorithm (priority, deadline urgency, "
                "CPM critical path, downstream dependencies, and effort). Segregates tasks into "
                "recommended (ready to execute), blocked (waiting on prerequisites), and completed.",
)
async def get_project_priority_schedule(
    project_id: UUID,
    reference_date: Optional[date] = Query(None, description="Evaluation reference date (defaults to today)"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    if current_user:
        await verify_project_access(project_id=project_id, current_user=current_user, db=db)
    return await SchedulingService.calculate_project_priority_schedule(
        project_id=project_id,
        db=db,
        reference_date=reference_date,
    )


@router.post(
    "/{project_id}/schedule/pert",
    response_model=PertAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Run PERT Three-Point Duration & Probability Analysis",
    description="Accepts optimistic, most-likely, and pessimistic duration estimates for project tasks. "
                "Computes expected duration, variance, standard deviation, and standard normal "
                "probability of meeting a target completion deadline along the critical path.",
)
async def analyze_project_pert(
    project_id: UUID,
    request: PertCalculationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    if current_user:
        await verify_project_access(project_id=project_id, current_user=current_user, db=db)
    return await SchedulingService.analyze_project_pert(
        project_id=project_id,
        request=request,
        db=db,
    )

