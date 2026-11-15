import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from app.algorithms.exceptions import InvalidPertEstimateError


@dataclass
class PertTaskEstimate:
    """Three-point time estimates and computed PERT values for a task."""
    id: Any
    optimistic: float
    most_likely: float
    pessimistic: float
    expected_duration: float = field(init=False)
    variance: float = field(init=False)
    standard_deviation: float = field(init=False)

    def __post_init__(self):
        if self.optimistic < 0.0:
            raise InvalidPertEstimateError(
                f"Optimistic duration for task '{self.id}' cannot be negative ({self.optimistic})."
            )
        if self.most_likely < 0.0:
            raise InvalidPertEstimateError(
                f"Most likely duration for task '{self.id}' cannot be negative ({self.most_likely})."
            )
        if self.pessimistic < 0.0:
            raise InvalidPertEstimateError(
                f"Pessimistic duration for task '{self.id}' cannot be negative ({self.pessimistic})."
            )
        if not (self.optimistic <= self.most_likely <= self.pessimistic):
            raise InvalidPertEstimateError(
                f"Invalid estimate ordering for task '{self.id}': "
                f"must satisfy Optimistic ({self.optimistic}) <= "
                f"Most Likely ({self.most_likely}) <= "
                f"Pessimistic ({self.pessimistic})."
            )

        self.expected_duration = round((self.optimistic + 4.0 * self.most_likely + self.pessimistic) / 6.0, 4)
        sigma = (self.pessimistic - self.optimistic) / 6.0
        self.variance = round(sigma ** 2, 4)
        self.standard_deviation = round(sigma, 4)


@dataclass
class PertAnalysisResult:
    """Consolidated project PERT analysis result with deadline probability."""
    tasks: Dict[Any, PertTaskEstimate]
    critical_path_expected_duration: float
    critical_path_variance: float
    critical_path_std_dev: float
    target_deadline: Optional[float] = None
    z_score: Optional[float] = None
    probability_of_meeting_deadline: Optional[float] = None
    confidence_percentage: Optional[float] = None
    assumptions: List[str] = field(default_factory=list)


def calculate_normal_cdf(z: float) -> float:
    """
    Computes standard normal cumulative distribution function (CDF)
    using math.erf from the Python standard library.
    """
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def analyze_pert(
    task_estimates: List[PertTaskEstimate],
    critical_path_task_ids: Optional[List[Any]] = None,
    target_deadline_hours: Optional[float] = None,
) -> PertAnalysisResult:
    """
    Executes Program Evaluation and Review Technique (PERT) analysis.
    
    Integrates individual three-point estimates with the critical path to compute
    project expected duration, variance, and normal distribution deadline probability.
    """
    estimates_dict = {t.id: t for t in task_estimates}

    # If critical path is not provided, use all tasks as reference
    cp_ids = critical_path_task_ids if critical_path_task_ids is not None else list(estimates_dict.keys())
    
    # Calculate critical path sum of expected durations and variances
    cp_expected_duration = 0.0
    cp_variance = 0.0

    for tid in cp_ids:
        if tid in estimates_dict:
            cp_expected_duration += estimates_dict[tid].expected_duration
            cp_variance += estimates_dict[tid].variance

    cp_expected_duration = round(cp_expected_duration, 4)
    cp_variance = round(cp_variance, 4)
    cp_std_dev = round(math.sqrt(cp_variance), 4)

    z_score = None
    probability = None
    confidence_pct = None

    if target_deadline_hours is not None:
        if target_deadline_hours < 0:
            raise InvalidPertEstimateError("Target deadline duration cannot be negative.")
        
        if cp_std_dev == 0.0:
            if target_deadline_hours >= cp_expected_duration:
                probability = 1.0
            else:
                probability = 0.0
            z_score = 0.0
        else:
            z_score = round((target_deadline_hours - cp_expected_duration) / cp_std_dev, 4)
            raw_prob = calculate_normal_cdf(z_score)
            # Bound probability within [0.0001, 0.9999] for numerical realism
            probability = round(min(max(raw_prob, 0.0001), 0.9999), 4)
        
        confidence_pct = round(probability * 100.0, 2)

    assumptions = [
        "Individual task durations approximate beta distributions.",
        "Task durations along the critical path are assumed statistically independent.",
        "Total project duration approximates a Normal distribution under the Central Limit Theorem.",
        "Probabilities are estimation guidelines for academic planning and do not constitute absolute guarantees.",
    ]

    return PertAnalysisResult(
        tasks=estimates_dict,
        critical_path_expected_duration=cp_expected_duration,
        critical_path_variance=cp_variance,
        critical_path_std_dev=cp_std_dev,
        target_deadline=target_deadline_hours,
        z_score=z_score,
        probability_of_meeting_deadline=probability,
        confidence_percentage=confidence_pct,
        assumptions=assumptions,
    )
