from datetime import date, datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.models.enums import TaskStatus, TaskPriority


class TaskBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    milestone_id: Optional[UUID] = None
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    estimated_duration_hours: float = Field(..., ge=0.0, description="Estimated work hours")
    actual_duration_hours: Optional[float] = Field(None, ge=0.0)
    start_date: Optional[date] = None
    due_date: date

    @model_validator(mode="after")
    def validate_dates(self) -> "TaskBase":
        if self.start_date and self.due_date:
            if self.due_date < self.start_date:
                raise ValueError("due_date cannot be earlier than start_date")
        return self


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=200)
    description: Optional[str] = None
    milestone_id: Optional[UUID] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    estimated_duration_hours: Optional[float] = Field(None, ge=0.0)
    actual_duration_hours: Optional[float] = Field(None, ge=0.0)
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    completed_at: Optional[datetime] = None

    @model_validator(mode="after")
    def validate_update_dates(self) -> "TaskUpdate":
        if self.start_date and self.due_date:
            if self.due_date < self.start_date:
                raise ValueError("due_date cannot be earlier than start_date")
        return self


from app.schemas.assignment import TaskAssignmentRead


class TaskRead(TaskBase):
    id: UUID
    project_id: UUID
    completed_at: Optional[datetime] = None
    created_by_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    assignments: List[TaskAssignmentRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class TaskSummary(BaseModel):
    id: UUID
    title: str
    status: TaskStatus
    priority: TaskPriority
    estimated_duration_hours: float
    due_date: date

    model_config = ConfigDict(from_attributes=True)
