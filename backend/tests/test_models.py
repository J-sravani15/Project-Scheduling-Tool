import pytest
from app.core.database import Base
from app.models import (
    User,
    AcademicProject,
    ProjectMember,
    AcademicMilestone,
    Task,
    TaskAssignment,
    TaskDependency,
    ProjectReview,
    ProjectNotification,
)


def test_models_registered_in_metadata():
    expected_tables = {
        "users",
        "academic_projects",
        "project_members",
        "academic_milestones",
        "tasks",
        "task_assignments",
        "task_dependencies",
        "project_reviews",
        "project_notifications",
    }
    actual_tables = set(Base.metadata.tables.keys())
    assert expected_tables.issubset(actual_tables), f"Missing tables: {expected_tables - actual_tables}"


def test_users_table_structure():
    table = Base.metadata.tables["users"]
    assert "email" in table.c
    assert "password_hash" in table.c
    assert "role" in table.c
    assert "is_active" in table.c
    assert table.c.email.unique or any(idx.unique and "email" in idx.columns for idx in table.indexes)


def test_tasks_table_constraints_and_indexes():
    table = Base.metadata.tables["tasks"]
    constraint_names = {c.name for c in table.constraints if c.name}
    assert "ck_task_estimated_duration_positive" in constraint_names
    assert "ck_task_actual_duration_positive" in constraint_names
    assert "ck_task_dates_valid" in constraint_names

    index_names = {idx.name for idx in table.indexes}
    assert "ix_tasks_project_status" in index_names
    assert "ix_tasks_project_priority" in index_names
    assert "ix_tasks_project_due_date" in index_names


def test_task_dependencies_table_constraints():
    table = Base.metadata.tables["task_dependencies"]
    constraint_names = {c.name for c in table.constraints if c.name}
    assert "ck_no_self_dependency" in constraint_names
    assert "uq_task_dependency_pair" in constraint_names


def test_academic_projects_table_constraints():
    table = Base.metadata.tables["academic_projects"]
    constraint_names = {c.name for c in table.constraints if c.name}
    assert "ck_project_date_range" in constraint_names
    assert "ck_project_semester_range" in constraint_names


def test_project_reviews_table_constraints():
    table = Base.metadata.tables["project_reviews"]
    constraint_names = {c.name for c in table.constraints if c.name}
    assert "uq_project_review_number" in constraint_names
    assert "ck_review_number_positive" in constraint_names
    assert "ck_review_score_range" in constraint_names
