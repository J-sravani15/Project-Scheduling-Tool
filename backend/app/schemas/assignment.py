from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from app.schemas.user import UserSummary


class TaskAssignmentBase(BaseModel):
    user_id: UUID


class TaskAssignmentCreate(TaskAssignmentBase):
    pass


class TaskAssignmentRead(BaseModel):
    id: UUID
    task_id: UUID
    user_id: UUID
    assigned_by_id: Optional[UUID] = None
    assigned_at: datetime
    user: Optional[UserSummary] = None

    model_config = ConfigDict(from_attributes=True)
