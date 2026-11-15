import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import (
    Text,
    Integer,
    Float,
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
from app.models.enums import ReviewStatus

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.project import AcademicProject


class ProjectReview(Base):
    """
    Represents an academic project evaluation/review session conducted by a faculty guide.
    """
    __tablename__ = "project_reviews"

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
    faculty_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    review_number: Mapped[int] = mapped_column(Integer, nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[ReviewStatus] = mapped_column(
        SQLEnum(ReviewStatus, native_enum=False, length=30),
        nullable=False,
        default=ReviewStatus.SCHEDULED,
        index=True,
    )
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

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
        UniqueConstraint("project_id", "review_number", name="uq_project_review_number"),
        CheckConstraint("review_number >= 1", name="ck_review_number_positive"),
        CheckConstraint(
            "score IS NULL OR (score >= 0.0 AND score <= 100.0)",
            name="ck_review_score_range",
        ),
    )

    # Relationships
    project: Mapped["AcademicProject"] = relationship(
        "AcademicProject",
        back_populates="reviews",
        foreign_keys=[project_id],
    )
    faculty: Mapped["User"] = relationship(
        "User",
        back_populates="conducted_reviews",
        foreign_keys=[faculty_id],
    )

    def __repr__(self) -> str:
        return f"<ProjectReview(id={self.id}, project_id={self.project_id}, rev_num={self.review_number}, status='{self.status}')>"
