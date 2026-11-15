import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import (
    String,
    Text,
    Float,
    Date,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
    CheckConstraint,
    Enum as SQLEnum,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.enums import TaskStatus, TaskPriority, DependencyType

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.project import AcademicProject
    from app.models.milestone import AcademicMilestone


class Task(Base):
    """
    Represents an individual work package or task within an academic project.
    """
    __tablename__ = "tasks"

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
    milestone_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("academic_milestones.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[TaskStatus] = mapped_column(
        SQLEnum(TaskStatus, native_enum=False, length=30),
        nullable=False,
        default=TaskStatus.TODO,
        index=True,
    )
    priority: Mapped[TaskPriority] = mapped_column(
        SQLEnum(TaskPriority, native_enum=False, length=30),
        nullable=False,
        default=TaskPriority.MEDIUM,
        index=True,
    )
    estimated_duration_hours: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    actual_duration_hours: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
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
        CheckConstraint("estimated_duration_hours >= 0", name="ck_task_estimated_duration_positive"),
        CheckConstraint(
            "actual_duration_hours IS NULL OR actual_duration_hours >= 0",
            name="ck_task_actual_duration_positive",
        ),
        CheckConstraint("start_date IS NULL OR due_date >= start_date", name="ck_task_dates_valid"),
        Index("ix_tasks_project_status", "project_id", "status"),
        Index("ix_tasks_project_priority", "project_id", "priority"),
        Index("ix_tasks_project_due_date", "project_id", "due_date"),
    )

    # Relationships
    project: Mapped["AcademicProject"] = relationship(
        "AcademicProject",
        back_populates="tasks",
        foreign_keys=[project_id],
    )
    milestone: Mapped[Optional["AcademicMilestone"]] = relationship(
        "AcademicMilestone",
        back_populates="tasks",
        foreign_keys=[milestone_id],
    )
    creator: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by_id],
    )
    assignments: Mapped[List["TaskAssignment"]] = relationship(
        "TaskAssignment",
        back_populates="task",
        foreign_keys="TaskAssignment.task_id",
        cascade="all, delete-orphan",
    )
    # Tasks that must finish before this task can start (this task is dependent)
    prerequisite_dependencies: Mapped[List["TaskDependency"]] = relationship(
        "TaskDependency",
        back_populates="task",
        foreign_keys="TaskDependency.task_id",
        cascade="all, delete-orphan",
    )
    # Tasks that depend on this task (this task is prerequisite)
    dependent_tasks: Mapped[List["TaskDependency"]] = relationship(
        "TaskDependency",
        back_populates="depends_on_task",
        foreign_keys="TaskDependency.depends_on_task_id",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, title='{self.title}', status='{self.status}', priority='{self.priority}')>"


class TaskAssignment(Base):
    """
    Associates tasks with student team members.
    """
    __tablename__ = "task_assignments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assigned_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("task_id", "user_id", name="uq_task_user_assignment"),
    )

    # Relationships
    task: Mapped["Task"] = relationship(
        "Task",
        back_populates="assignments",
        foreign_keys=[task_id],
    )
    user: Mapped["User"] = relationship(
        "User",
        back_populates="assigned_tasks",
        foreign_keys=[user_id],
    )
    assigned_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[assigned_by_id],
    )

    def __repr__(self) -> str:
        return f"<TaskAssignment(task_id={self.task_id}, user_id={self.user_id})>"


class TaskDependency(Base):
    """
    Represents prerequisite relationships between tasks (DAG edges for CPM & PERT).
    task_id is the dependent task (successor).
    depends_on_task_id is the prerequisite task (predecessor).
    Note: Cycle detection is enforced at application/service level.
    """
    __tablename__ = "task_dependencies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    depends_on_task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dependency_type: Mapped[DependencyType] = mapped_column(
        SQLEnum(DependencyType, native_enum=False, length=30),
        nullable=False,
        default=DependencyType.FINISH_TO_START,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("task_id", "depends_on_task_id", name="uq_task_dependency_pair"),
        CheckConstraint("task_id != depends_on_task_id", name="ck_no_self_dependency"),
    )

    # Relationships
    task: Mapped["Task"] = relationship(
        "Task",
        back_populates="prerequisite_dependencies",
        foreign_keys=[task_id],
    )
    depends_on_task: Mapped["Task"] = relationship(
        "Task",
        back_populates="dependent_tasks",
        foreign_keys=[depends_on_task_id],
    )

    def __repr__(self) -> str:
        return f"<TaskDependency(task={self.task_id} -> depends_on={self.depends_on_task_id})>"
