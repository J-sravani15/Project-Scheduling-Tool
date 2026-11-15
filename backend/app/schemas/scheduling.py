from datetime import date
from typing import Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.models.enums import TaskPriority, TaskStatus


# --- CPM SCHEMAS ---

class CpmTaskMetric(BaseModel):
    id: UUID
    title: str
    duration: float
    early_start: float
    early_finish: float
    late_start: float
    late_finish: float
    slack: float
    is_critical: bool

    model_config = ConfigDict(from_attributes=True)


class CpmAnalysisResponse(BaseModel):
    project_id: UUID
    total_project_duration_hours: float
    critical_tasks: List[UUID]
    critical_paths: List[List[UUID]]
    tasks: Dict[str, CpmTaskMetric]
    warnings: List[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# --- PERT SCHEMAS ---

class PertTaskEstimateInput(BaseModel):
    task_id: UUID
    optimistic_hours: float = Field(..., ge=0.0, description="Minimum duration (best-case scenario)")
    most_likely_hours: float = Field(..., ge=0.0, description="Modal duration (most probable scenario)")
    pessimistic_hours: float = Field(..., ge=0.0, description="Maximum duration (worst-case scenario)")

    @model_validator(mode="after")
    def validate_three_point_ordering(self) -> "PertTaskEstimateInput":
        if not (self.optimistic_hours <= self.most_likely_hours <= self.pessimistic_hours):
            raise ValueError(
                f"Three-point estimates must satisfy optimistic ({self.optimistic_hours}) <= "
                f"most_likely ({self.most_likely_hours}) <= pessimistic ({self.pessimistic_hours})."
            )
        return self


class PertCalculationRequest(BaseModel):
    target_deadline_hours: Optional[float] = Field(
        None, ge=0.0, description="Target completion duration to evaluate probability for"
    )
    estimates: List[PertTaskEstimateInput] = Field(
        ..., min_length=1, description="List of three-point duration estimates"
    )


class PertTaskMetric(BaseModel):
    task_id: UUID
    optimistic_hours: float
    most_likely_hours: float
    pessimistic_hours: float
    expected_duration_hours: float
    variance: float
    standard_deviation: float

    model_config = ConfigDict(from_attributes=True)


class PertAnalysisResponse(BaseModel):
    project_id: UUID
    critical_path_expected_duration_hours: float
    critical_path_variance: float
    critical_path_std_dev: float
    target_deadline_hours: Optional[float] = None
    z_score: Optional[float] = None
    probability_of_meeting_deadline: Optional[float] = None
    confidence_percentage: Optional[float] = None
    tasks: Dict[str, PertTaskMetric]
    assumptions: List[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# --- PRIORITY SCHEDULING SCHEMAS ---

class ScoreBreakdownSchema(BaseModel):
    priority_norm: float
    urgency_norm: float
    critical_norm: float
    downstream_norm: float
    effort_norm: float
    weighted_total: float

    model_config = ConfigDict(from_attributes=True)


class PriorityTaskOutputSchema(BaseModel):
    id: UUID
    title: str
    priority: TaskPriority
    status: TaskStatus
    due_date: Optional[date] = None
    estimated_duration_hours: Optional[float] = None
    is_eligible: bool
    blocking_prerequisites: List[UUID]
    is_critical: bool
    downstream_dependents_count: int
    total_score: float
    score_breakdown: ScoreBreakdownSchema
    recommendation_reason: str

    model_config = ConfigDict(from_attributes=True)


class PriorityScheduleResponse(BaseModel):
    project_id: UUID
    recommended_tasks: List[PriorityTaskOutputSchema]
    blocked_tasks: List[PriorityTaskOutputSchema]
    completed_tasks: List[PriorityTaskOutputSchema]
    weights: Dict[str, float]

    model_config = ConfigDict(from_attributes=True)
