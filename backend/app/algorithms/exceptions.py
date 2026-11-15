from typing import List, Any


class SchedulingError(Exception):
    """Base exception for scheduling algorithm errors."""
    pass


class CycleDetectedError(SchedulingError):
    """Raised when a dependency cycle is detected in the task graph."""
    def __init__(self, cycle_path: List[Any]):
        self.cycle_path = cycle_path
        path_str = " -> ".join(str(node) for node in cycle_path)
        super().__init__(f"Dependency cycle detected in task graph: {path_str}")


class InvalidDependencyError(SchedulingError):
    """Raised when a dependency edge is invalid (e.g., self-reference, unknown task, cross-project)."""
    pass


class InvalidDurationError(SchedulingError):
    """Raised when task duration is missing, negative, or invalid."""
    pass


class InvalidPertEstimateError(SchedulingError):
    """Raised when three-point PERT estimates violate O <= M <= P or non-negativity."""
    pass
