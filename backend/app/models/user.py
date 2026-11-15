import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List
from sqlalchemy import String, Boolean, DateTime, Enum as SQLEnum, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.enums import UserRole

if TYPE_CHECKING:
    from app.models.project import AcademicProject, ProjectMember
    from app.models.task import TaskAssignment
    from app.models.review import ProjectReview
    from app.models.notification import ProjectNotification


class User(Base):
    """
    Represents students and faculty guides in the academic institution.
    """
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole, native_enum=False, length=20),
        nullable=False,
        default=UserRole.STUDENT,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
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

    # Relationships
    owned_projects: Mapped[List["AcademicProject"]] = relationship(
        "AcademicProject",
        back_populates="owner",
        foreign_keys="AcademicProject.owner_id",
        cascade="all, delete-orphan",
    )
    supervised_projects: Mapped[List["AcademicProject"]] = relationship(
        "AcademicProject",
        back_populates="faculty_guide",
        foreign_keys="AcademicProject.faculty_guide_id",
    )
    project_memberships: Mapped[List["ProjectMember"]] = relationship(
        "ProjectMember",
        back_populates="user",
        foreign_keys="ProjectMember.user_id",
        cascade="all, delete-orphan",
    )
    assigned_tasks: Mapped[List["TaskAssignment"]] = relationship(
        "TaskAssignment",
        back_populates="user",
        foreign_keys="TaskAssignment.user_id",
        cascade="all, delete-orphan",
    )
    conducted_reviews: Mapped[List["ProjectReview"]] = relationship(
        "ProjectReview",
        back_populates="faculty",
        foreign_keys="ProjectReview.faculty_id",
    )
    notifications: Mapped[List["ProjectNotification"]] = relationship(
        "ProjectNotification",
        back_populates="recipient",
        foreign_keys="ProjectNotification.recipient_id",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', role='{self.role}')>"
