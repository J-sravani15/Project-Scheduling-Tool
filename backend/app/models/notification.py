import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import (
    String,
    Text,
    DateTime,
    ForeignKey,
    Index,
    Enum as SQLEnum,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.enums import NotificationType

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.project import AcademicProject
    from app.models.task import Task


class ProjectNotification(Base):
    """
    Represents reminders and milestone/task alerts for students and faculty.
    """
    __tablename__ = "project_notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("academic_projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    recipient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    notification_type: Mapped[NotificationType] = mapped_column(
        SQLEnum(NotificationType, native_enum=False, length=40),
        nullable=False,
        default=NotificationType.GENERAL,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    task_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    link_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_notifications_recipient_read", "recipient_id", "read_at"),
    )

    # Relationships
    project: Mapped[Optional["AcademicProject"]] = relationship(
        "AcademicProject",
        back_populates="notifications",
        foreign_keys=[project_id],
    )
    recipient: Mapped["User"] = relationship(
        "User",
        back_populates="notifications",
        foreign_keys=[recipient_id],
    )
    task: Mapped[Optional["Task"]] = relationship(
        "Task",
        foreign_keys=[task_id],
    )

    def __repr__(self) -> str:
        return f"<ProjectNotification(id={self.id}, type='{self.notification_type}', recipient={self.recipient_id})>"
