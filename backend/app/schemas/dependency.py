from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, model_validator
from app.models.enums import DependencyType


class TaskDependencyBase(BaseModel):
    depends_on_task_id: UUID
    dependency_type: DependencyType = DependencyType.FINISH_TO_START


class TaskDependencyCreate(TaskDependencyBase):
    task_id: UUID

    @model_validator(mode="after")
    def validate_no_self_dependency(self) -> "TaskDependencyCreate":
        if self.task_id == self.depends_on_task_id:
            raise ValueError("A task cannot depend on itself (self-dependency prohibited)")
        return self


class TaskDependencyRead(TaskDependencyBase):
    id: UUID
    task_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
