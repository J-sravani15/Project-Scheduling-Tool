from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import NotificationType


class ProjectNotificationBase(BaseModel):
    notification_type: NotificationType = NotificationType.GENERAL
    title: str = Field(..., min_length=2, max_length=200)
    message: str = Field(..., min_length=2)
    task_id: Optional[UUID] = None
    link_url: Optional[str] = None
    scheduled_at: Optional[datetime] = None


class ProjectNotificationCreate(ProjectNotificationBase):
    project_id: Optional[UUID] = None
    recipient_id: UUID


class ProjectNotificationUpdate(BaseModel):
    read_at: Optional[datetime] = None


class ProjectNotificationRead(ProjectNotificationBase):
    id: UUID
    project_id: Optional[UUID] = None
    recipient_id: UUID
    sent_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    items: List[ProjectNotificationRead]
    unread_count: int
    total_count: int

    model_config = ConfigDict(from_attributes=True)
