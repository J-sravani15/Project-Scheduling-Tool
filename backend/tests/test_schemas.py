import pytest
from datetime import date, datetime, timezone
import uuid
from pydantic import ValidationError

from app.models.enums import (
    UserRole,
    ProjectStatus,
    ProjectType,
    TeamRole,
    MilestoneType,
    MilestoneStatus,
    TaskStatus,
    TaskPriority,
    DependencyType,
    ReviewStatus,
    NotificationType,
)
from app.schemas import (
    UserCreate,
    UserRead,
    UserSummary,
    AcademicProjectCreate,
    AcademicProjectRead,
    ProjectMemberCreate,
    AcademicMilestoneCreate,
    TaskCreate,
    TaskDependencyCreate,
    ProjectReviewCreate,
    ProjectNotificationCreate,
)


def test_user_create_and_email_normalization():
    user_in = UserCreate(
        full_name="Alice Smith",
        email="  ALICE.Smith@College.EDU  ",
        role=UserRole.STUDENT,
        password="securePassword123!",
    )
    assert user_in.email == "alice.smith@college.edu"
    assert user_in.full_name == "Alice Smith"
    assert user_in.role == UserRole.STUDENT


def test_user_read_excludes_password_hash():
    user_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    
    # UserRead should serialize without exposing any password or hash
    user_read = UserRead(
        id=user_id,
        full_name="Bob Jones",
        email="bob@college.edu",
        role=UserRole.FACULTY,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    
    data = user_read.model_dump()
    assert "password" not in data
    assert "password_hash" not in data
    assert data["role"] == UserRole.FACULTY


def test_academic_project_date_validation():
    # Valid date range
    proj = AcademicProjectCreate(
        title="AI Scheduling System",
        description="Final year project",
        academic_year="2025-2026",
        semester=8,
        department="Computer Science",
        project_type=ProjectType.CAPSTONE,
        status=ProjectStatus.PLANNING,
        start_date=date(2026, 1, 10),
        target_deadline=date(2026, 5, 15),
    )
    assert proj.title == "AI Scheduling System"

    # Invalid date range: target_deadline before start_date
    with pytest.raises(ValidationError) as exc_info:
        AcademicProjectCreate(
            title="AI Scheduling System",
            academic_year="2025-2026",
            semester=8,
            department="Computer Science",
            start_date=date(2026, 6, 1),
            target_deadline=date(2026, 5, 1),
        )
    assert "target_deadline cannot be earlier than start_date" in str(exc_info.value)


def test_task_duration_and_date_validation():
    # Valid task
    task = TaskCreate(
        title="Implement Forward Pass",
        status=TaskStatus.TODO,
        priority=TaskPriority.HIGH,
        estimated_duration_hours=12.5,
        start_date=date(2026, 2, 1),
        due_date=date(2026, 2, 10),
    )
    assert task.estimated_duration_hours == 12.5

    # Negative duration rejected
    with pytest.raises(ValidationError):
        TaskCreate(
            title="Implement Forward Pass",
            estimated_duration_hours=-5.0,
            due_date=date(2026, 2, 10),
        )

    # due_date before start_date rejected
    with pytest.raises(ValidationError):
        TaskCreate(
            title="Implement Forward Pass",
            estimated_duration_hours=4.0,
            start_date=date(2026, 2, 15),
            due_date=date(2026, 2, 10),
        )


def test_task_dependency_self_reference_rejection():
    task_id = uuid.uuid4()
    with pytest.raises(ValidationError) as exc_info:
        TaskDependencyCreate(
            task_id=task_id,
            depends_on_task_id=task_id,
            dependency_type=DependencyType.FINISH_TO_START,
        )
    assert "self-dependency prohibited" in str(exc_info.value)


def test_project_review_validation():
    faculty_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    
    # Valid review
    review = ProjectReviewCreate(
        faculty_id=faculty_id,
        review_number=1,
        scheduled_at=now,
        status=ReviewStatus.SCHEDULED,
        score=85.5,
    )
    assert review.review_number == 1
    assert review.score == 85.5

    # Invalid score > 100
    with pytest.raises(ValidationError):
        ProjectReviewCreate(
            faculty_id=faculty_id,
            review_number=1,
            scheduled_at=now,
            score=105.0,
        )

    # Invalid review number < 1
    with pytest.raises(ValidationError):
        ProjectReviewCreate(
            faculty_id=faculty_id,
            review_number=0,
            scheduled_at=now,
        )


def test_milestone_validation():
    milestone = AcademicMilestoneCreate(
        title="System Design Document",
        milestone_type=MilestoneType.SYSTEM_DESIGN,
        sequence_number=3,
        planned_date=date(2026, 3, 1),
        status=MilestoneStatus.PENDING,
    )
    assert milestone.sequence_number == 3
    assert milestone.is_required is True

    # Invalid sequence number < 1
    with pytest.raises(ValidationError):
        AcademicMilestoneCreate(
            title="System Design Document",
            sequence_number=0,
            planned_date=date(2026, 3, 1),
        )
