from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class ReadinessBreakdown(BaseModel):
    milestone_score: float = Field(..., description="Milestone completion (max 40 pts)")
    task_completion_score: float = Field(..., description="Overall task completion (max 15 pts)")
    critical_path_score: float = Field(..., description="Critical path health (max 15 pts)")
    overdue_score: float = Field(..., description="Deadline punctuality (max 20 pts)")
    review_timing_score: float = Field(..., description="Upcoming review readiness (max 10 pts)")
    total_score: float = Field(..., description="Composite readiness score (0 - 100)")

    model_config = ConfigDict(from_attributes=True)


class ReviewReadinessResponse(BaseModel):
    project_id: UUID
    readiness_score: float
    readiness_level: str
    score_breakdown: ReadinessBreakdown
    blockers: List[str] = Field(default_factory=list)
    actionable_recommendations: List[str] = Field(default_factory=list)
    next_review_scheduled_at: Optional[datetime] = None
    is_advisory_notice: str = "This scorecard is an advisory planning metric for academic milestones and not an automated grading verdict."

    model_config = ConfigDict(from_attributes=True)
