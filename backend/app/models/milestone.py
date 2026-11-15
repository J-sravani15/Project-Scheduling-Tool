import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import (
    String,
    Text,
    Integer,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    Enum as SQLEnum,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.enums import MilestoneType, MilestoneStatus

if TYPE_CHECKING:
    from app.models.project import AcademicProject
    from app.models.task import Task


class AcademicMilestone(Base):
    """
    Represents an academic milestone/checkpoint (Proposal, Review 1, Review 2, Final Viva)
    for a project.
    """
    __tablename__ = "academic_milestones"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("academic_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    milestone_type: Mapped[MilestoneType] = mapped_column(
        SQLEnum(MilestoneType, native_enum=False, length=40),
        nullable=False,
        default=MilestoneType.CUSTOM,
    )
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    planned_date: Mapped[date] = mapped_column(Date, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[MilestoneStatus] = mapped_column(
        SQLEnum(MilestoneStatus, native_enum=False, length=30),
        nullable=False,
        default=MilestoneStatus.PENDING,
        index=True,
    )
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("project_id", "sequence_number", name="uq_project_milestone_sequence"),
        CheckConstraint("sequence_number >= 1", name="ck_milestone_sequence_positive"),
    )

    # Relationships
    project: Mapped["AcademicProject"] = relationship(
        "AcademicProject",
        back_populates="milestones",
        foreign_keys=[project_id],
    )
    tasks: Mapped[List["Task"]] = relationship(
        "Task",
        back_populates="milestone",
        foreign_keys="Task.milestone_id",
    )

    def __repr__(self) -> str:
        return f"<AcademicMilestone(id={self.id}, project_id={self.project_id}, seq={self.sequence_number}, title='{self.title}')>"
