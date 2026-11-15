import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import (
    String,
    Text,
    Integer,
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
from app.models.enums import ProjectStatus, ProjectType, TeamRole

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.milestone import AcademicMilestone
    from app.models.task import Task
    from app.models.review import ProjectReview
    from app.models.notification import ProjectNotification


class AcademicProject(Base):
    """
    Represents an academic project (Capstone, Major, Minor, Research)
    managed by a student or a team, with optional faculty supervision.
    """
    __tablename__ = "academic_projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    academic_year: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g., "2025-2026"
    semester: Mapped[int] = mapped_column(Integer, nullable=False)          # e.g., 7 or 8
    department: Mapped[str] = mapped_column(String(100), nullable=False)
    project_type: Mapped[ProjectType] = mapped_column(
        SQLEnum(ProjectType, native_enum=False, length=30),
        nullable=False,
        default=ProjectType.CAPSTONE,
    )
    status: Mapped[ProjectStatus] = mapped_column(
        SQLEnum(ProjectStatus, native_enum=False, length=30),
        nullable=False,
        default=ProjectStatus.PLANNING,
        index=True,
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    target_deadline: Mapped[date] = mapped_column(Date, nullable=False)
    actual_completion_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    faculty_guide_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

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
        CheckConstraint("target_deadline >= start_date", name="ck_project_date_range"),
        CheckConstraint("semester >= 1 AND semester <= 12", name="ck_project_semester_range"),
    )

    # Relationships
    owner: Mapped["User"] = relationship(
        "User",
        back_populates="owned_projects",
        foreign_keys=[owner_id],
    )
    faculty_guide: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="supervised_projects",
        foreign_keys=[faculty_guide_id],
    )
    members: Mapped[List["ProjectMember"]] = relationship(
        "ProjectMember",
        back_populates="project",
        foreign_keys="ProjectMember.project_id",
        cascade="all, delete-orphan",
    )
    milestones: Mapped[List["AcademicMilestone"]] = relationship(
        "AcademicMilestone",
        back_populates="project",
        foreign_keys="AcademicMilestone.project_id",
        cascade="all, delete-orphan",
        order_by="AcademicMilestone.sequence_number",
    )
    tasks: Mapped[List["Task"]] = relationship(
        "Task",
        back_populates="project",
        foreign_keys="Task.project_id",
        cascade="all, delete-orphan",
    )
    reviews: Mapped[List["ProjectReview"]] = relationship(
        "ProjectReview",
        back_populates="project",
        foreign_keys="ProjectReview.project_id",
        cascade="all, delete-orphan",
        order_by="ProjectReview.review_number",
    )
    notifications: Mapped[List["ProjectNotification"]] = relationship(
        "ProjectNotification",
        back_populates="project",
        foreign_keys="ProjectNotification.project_id",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<AcademicProject(id={self.id}, title='{self.title}', status='{self.status}')>"


class ProjectMember(Base):
    """
    Associates a student team member with an academic project.
    """
    __tablename__ = "project_members"

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
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    team_role: Mapped[TeamRole] = mapped_column(
        SQLEnum(TeamRole, native_enum=False, length=30),
        nullable=False,
        default=TeamRole.MEMBER,
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_project_member"),
    )

    # Relationships
    project: Mapped["AcademicProject"] = relationship(
        "AcademicProject",
        back_populates="members",
        foreign_keys=[project_id],
    )
    user: Mapped["User"] = relationship(
        "User",
        back_populates="project_memberships",
        foreign_keys=[user_id],
    )

    def __repr__(self) -> str:
        return f"<ProjectMember(project_id={self.project_id}, user_id={self.user_id}, role='{self.team_role}')>"
