from datetime import date
from typing import List
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class StudentWorkloadSummary(BaseModel):
    user_id: UUID
    full_name: str
    email: str
    team_role: str
    total_active_hours: float
    completed_hours: float
    assigned_task_count: int
    overdue_task_count: int
    upcoming_task_count: int
    completed_task_count: int
    is_overloaded: bool
    is_underutilized: bool

    model_config = ConfigDict(from_attributes=True)


class TeamWorkloadResponse(BaseModel):
    project_id: UUID
    threshold_hours: float
    reference_date: date
    total_team_active_hours: float
    average_hours_per_student: float
    workload_standard_deviation: float
    student_workloads: List[StudentWorkloadSummary]
    overloaded_students: List[UUID]
    underutilized_students: List[UUID]
    recommendations: List[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
