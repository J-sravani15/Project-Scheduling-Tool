from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import ReviewStatus
from app.schemas.user import UserSummary


class ProjectReviewBase(BaseModel):
    review_number: int = Field(..., ge=1, description="Sequential review number (1, 2, 3...)")
    scheduled_at: datetime
    status: ReviewStatus = ReviewStatus.SCHEDULED
    feedback: Optional[str] = None
    score: Optional[float] = Field(None, ge=0.0, le=100.0, description="Evaluation score out of 100")


class ProjectReviewCreate(ProjectReviewBase):
    faculty_id: Optional[UUID] = None


class ProjectReviewUpdate(BaseModel):
    scheduled_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: Optional[ReviewStatus] = None
    feedback: Optional[str] = None
    score: Optional[float] = Field(None, ge=0.0, le=100.0)


class ProjectReviewRead(ProjectReviewBase):
    id: UUID
    project_id: UUID
    faculty_id: UUID
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    faculty: Optional[UserSummary] = None

    model_config = ConfigDict(from_attributes=True)
