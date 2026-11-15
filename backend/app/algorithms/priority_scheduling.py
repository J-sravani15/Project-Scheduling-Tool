from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Set, Optional, Any
from app.models.enums import TaskStatus, TaskPriority
from app.algorithms.exceptions import (
    CycleDetectedError,
    InvalidDependencyError,
)
from app.algorithms.cpm import _find_cycle


@dataclass
class PriorityWeights:
    """Configurable weights for the multi-factor academic priority scoring model."""
    priority: float = 30.0       # Urgency of student task priority label
    urgency: float = 25.0        # Proximity to academic due date
    critical_path: float = 20.0  # Membership in CPM critical path
    downstream: float = 15.0     # Downstream blocking factor (number of dependent tasks)
    effort: float = 10.0         # Effort factor (quick-win bonuses for unblocking tasks)


@dataclass
class PriorityTaskInput:
    """Input representation of a task for Priority Scheduling."""
    id: Any
    title: str
    status: TaskStatus
    priority: TaskPriority
    due_date: Optional[date] = None
    estimated_duration_hours: Optional[float] = None
    prerequisites: Set[Any] = field(default_factory=set)
    is_critical: bool = False
    downstream_count: int = 0


@dataclass
class ComponentScoreBreakdown:
    """Normalized score breakdown (0.0 to 1.0) and weighted contributions."""
    priority_norm: float
    urgency_norm: float
    critical_norm: float
    downstream_norm: float
    effort_norm: float
    weighted_total: float


@dataclass
class RankedTaskOutput:
    """Comprehensive output for a ranked/evaluated task."""
    id: Any
    title: str
    priority: TaskPriority
    status: TaskStatus
    due_date: Optional[date]
    estimated_duration_hours: Optional[float]
    is_eligible: bool
    blocking_prerequisites: List[Any]
    is_critical: bool
    downstream_dependents_count: int
    total_score: float
    score_breakdown: ComponentScoreBreakdown
    recommendation_reason: str


@dataclass
class PriorityScheduleResult:
    """Result of the Priority Scheduling algorithm."""
    recommended_tasks: List[RankedTaskOutput]
    blocked_tasks: List[RankedTaskOutput]
    completed_tasks: List[RankedTaskOutput]
    weights: PriorityWeights


def compute_priority_schedule(
    tasks: List[PriorityTaskInput],
    reference_date: Optional[date] = None,
    weights: Optional[PriorityWeights] = None,
) -> PriorityScheduleResult:
    """
    Ranks tasks using a deterministic multi-factor priority algorithm.
    
    1. Validates dependency graph & checks for cycles.
    2. Identifies task eligibility (all prerequisites must be COMPLETED).
    3. Normalizes 5 components: Priority, Due Date Urgency, CPM Criticality, Downstream Impact, Effort.
    4. Computes deterministic ranking with tie-breaking: (-total_score, due_date, str(id)).
    5. Returns separated queues: recommended (ready to do), blocked (waiting on prerequisites), and completed.
    """
    if weights is None:
        weights = PriorityWeights()
    if reference_date is None:
        reference_date = date.today()

    task_map: Dict[Any, PriorityTaskInput] = {t.id: t for t in tasks}

    # 1. Dependency Validation & Cycle Detection
    predecessors: Dict[Any, Set[Any]] = {t.id: set() for t in tasks}
    successors: Dict[Any, Set[Any]] = {t.id: set() for t in tasks}

    for t in tasks:
        for p in t.prerequisites:
            if p == t.id:
                raise InvalidDependencyError(f"Task '{t.id}' cannot depend on itself.")
            if p not in task_map:
                raise InvalidDependencyError(f"Task '{t.id}' depends on unknown task '{p}'.")
            predecessors[t.id].add(p)
            successors[p].add(t.id)

    # Topological cycle check using Kahn's algorithm
    in_degree = {tid: len(predecessors[tid]) for tid in task_map}
    ready_q = [tid for tid, deg in in_degree.items() if deg == 0]
    visited_count = 0

    while ready_q:
        curr = ready_q.pop()
        visited_count += 1
        for s in successors[curr]:
            in_degree[s] -= 1
            if in_degree[s] == 0:
                ready_q.append(s)

    if visited_count != len(task_map):
        cycle = _find_cycle(predecessors)
        raise CycleDetectedError(cycle)

    # 2. Compute Downstream Dependents Count for each task
    # A task's downstream impact is the number of reachable successors in the DAG
    downstream_counts: Dict[Any, int] = {}
    for tid in task_map:
        downstream_counts[tid] = len(_get_all_downstream(tid, successors))

    # 3. Categorize & Score Tasks
    recommended: List[RankedTaskOutput] = []
    blocked: List[RankedTaskOutput] = []
    completed: List[RankedTaskOutput] = []

    for t in tasks:
        # Check prerequisite completion
        blocking_prereqs = [
            p for p in sorted(predecessors[t.id], key=str)
            if task_map[p].status != TaskStatus.COMPLETED
        ]
        is_eligible = (len(blocking_prereqs) == 0) and (t.status != TaskStatus.COMPLETED)

        # Component 1: Priority score (0.0 to 1.0)
        prio_norm = _get_priority_norm(t.priority)

        # Component 2: Urgency score (0.0 to 1.0)
        urg_norm = _get_urgency_norm(t.due_date, reference_date)

        # Component 3: Critical Path score (0.0 or 1.0)
        crit_norm = 1.0 if t.is_critical else 0.0

        # Component 4: Downstream Impact score (0.0 to 1.0)
        downstream_cnt = downstream_counts[t.id]
        downstream_norm = min(1.0, downstream_cnt / 5.0)

        # Component 5: Effort score (0.0 to 1.0, quick wins get higher priority)
        eff_norm = _get_effort_norm(t.estimated_duration_hours)

        # Weighted total
        total_score = round(
            weights.priority * prio_norm
            + weights.urgency * urg_norm
            + weights.critical_path * crit_norm
            + weights.downstream * downstream_norm
            + weights.effort * eff_norm,
            2,
        )

        breakdown = ComponentScoreBreakdown(
            priority_norm=round(prio_norm, 2),
            urgency_norm=round(urg_norm, 2),
            critical_norm=round(crit_norm, 2),
            downstream_norm=round(downstream_norm, 2),
            effort_norm=round(eff_norm, 2),
            weighted_total=total_score,
        )

        reason = _generate_reason(t, is_eligible, blocking_prereqs, crit_norm, downstream_cnt, urg_norm)

        output = RankedTaskOutput(
            id=t.id,
            title=t.title,
            priority=t.priority,
            status=t.status,
            due_date=t.due_date,
            estimated_duration_hours=t.estimated_duration_hours,
            is_eligible=is_eligible,
            blocking_prerequisites=blocking_prereqs,
            is_critical=t.is_critical,
            downstream_dependents_count=downstream_cnt,
            total_score=total_score,
            score_breakdown=breakdown,
            recommendation_reason=reason,
        )

        if t.status == TaskStatus.COMPLETED:
            completed.append(output)
        elif is_eligible:
            recommended.append(output)
        else:
            blocked.append(output)

    # 4. Deterministic Sort for Recommended and Blocked Queues
    # Key: (-total_score, due_date (or distant date), str(id))
    max_date = date(9999, 12, 31)

    def sort_key(item: RankedTaskOutput):
        d = item.due_date if item.due_date is not None else max_date
        return (-item.total_score, d, str(item.id))

    recommended.sort(key=sort_key)
    blocked.sort(key=sort_key)
    completed.sort(key=sort_key)

    return PriorityScheduleResult(
        recommended_tasks=recommended,
        blocked_tasks=blocked,
        completed_tasks=completed,
        weights=weights,
    )


def _get_all_downstream(start_node: Any, successors: Dict[Any, Set[Any]]) -> Set[Any]:
    """Computes all transitive successors of a task in the DAG."""
    visited: Set[Any] = set()
    queue = list(successors[start_node])

    while queue:
        curr = queue.pop()
        if curr not in visited:
            visited.add(curr)
            queue.extend(successors[curr] - visited)

    return visited


def _get_priority_norm(p: TaskPriority) -> float:
    if p == TaskPriority.CRITICAL:
        return 1.0
    if p == TaskPriority.HIGH:
        return 0.75
    if p == TaskPriority.MEDIUM:
        return 0.50
    return 0.25  # LOW


def _get_urgency_norm(due_date: Optional[date], ref_date: date) -> float:
    if due_date is None:
        return 0.30  # neutral default for tasks without deadlines

    days_remaining = (due_date - ref_date).days
    if days_remaining <= 0:
        return 1.0   # overdue or due today
    if days_remaining <= 3:
        return 0.90
    if days_remaining <= 7:
        return 0.75
    if days_remaining <= 14:
        return 0.50
    if days_remaining <= 30:
        return 0.30
    return 0.10      # > 30 days away


def _get_effort_norm(hours: Optional[float]) -> float:
    if hours is None:
        return 0.50
    if hours <= 2.0:
        return 1.0   # very quick task
    if hours <= 6.0:
        return 0.75
    if hours <= 15.0:
        return 0.50
    return 0.25      # large effort task


def _generate_reason(
    t: PriorityTaskInput,
    is_eligible: bool,
    blocking_prereqs: List[Any],
    crit_norm: float,
    downstream_cnt: int,
    urg_norm: float,
) -> str:
    if t.status == TaskStatus.COMPLETED:
        return "Task has already been completed."
    if not is_eligible:
        return f"Blocked waiting on {len(blocking_prereqs)} prerequisite task(s)."

    reasons = []
    if crit_norm == 1.0:
        reasons.append("on the critical path")
    if urg_norm >= 0.9:
        reasons.append("approaching imminent deadline")
    if downstream_cnt > 0:
        reasons.append(f"blocks {downstream_cnt} downstream task(s)")
    if t.priority in (TaskPriority.CRITICAL, TaskPriority.HIGH):
        reasons.append(f"{t.priority.value} priority")

    if reasons:
        return "High priority because task is " + ", ".join(reasons) + "."
    return "Eligible task ready for execution."
