from datetime import date, datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import MilestoneType, MilestoneStatus


class AcademicMilestoneBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=150)
    description: Optional[str] = None
    milestone_type: MilestoneType = MilestoneType.CUSTOM
    sequence_number: int = Field(..., ge=1)
    planned_date: date
    status: MilestoneStatus = MilestoneStatus.PENDING
    is_required: bool = True


class AcademicMilestoneCreate(AcademicMilestoneBase):
    pass


class AcademicMilestoneUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=150)
    description: Optional[str] = None
    milestone_type: Optional[MilestoneType] = None
    sequence_number: Optional[int] = Field(None, ge=1)
    planned_date: Optional[date] = None
    completed_at: Optional[datetime] = None
    status: Optional[MilestoneStatus] = None
    is_required: Optional[bool] = None


class AcademicMilestoneRead(AcademicMilestoneBase):
    id: UUID
    project_id: UUID
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MilestoneTemplate(BaseModel):
    """Reusable template for standard academic project checkpoints."""
    title: str
    description: Optional[str] = None
    milestone_type: MilestoneType
    sequence_number: int
    offset_days_from_start: int
    is_required: bool = True
