from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from app.models.enums import TeamRole
from app.schemas.user import UserSummary


class ProjectMemberBase(BaseModel):
    user_id: UUID
    team_role: TeamRole = TeamRole.MEMBER


class ProjectMemberCreate(ProjectMemberBase):
    pass


class ProjectMemberUpdate(BaseModel):
    team_role: TeamRole


class ProjectMemberRead(BaseModel):
    id: UUID
    project_id: UUID
    user_id: UUID
    team_role: TeamRole
    joined_at: datetime
    user: Optional[UserSummary] = None

    model_config = ConfigDict(from_attributes=True)
