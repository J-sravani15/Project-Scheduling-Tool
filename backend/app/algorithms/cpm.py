from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any
from app.algorithms.exceptions import (
    CycleDetectedError,
    InvalidDependencyError,
    InvalidDurationError,
)


@dataclass
class CpmTaskInput:
    """Input representation of a task for CPM analysis."""
    id: Any
    duration: float
    prerequisites: Set[Any] = field(default_factory=set)
    title: Optional[str] = None


@dataclass
class CpmTaskOutput:
    """Computed CPM schedule metrics for a single task."""
    id: Any
    title: str
    duration: float
    early_start: float
    early_finish: float
    late_start: float
    late_finish: float
    slack: float
    is_critical: bool


@dataclass
class CpmResult:
    """Overall CPM schedule computation result."""
    total_duration: float
    critical_tasks: List[Any]
    critical_paths: List[List[Any]]
    tasks: Dict[Any, CpmTaskOutput]
    warnings: List[str] = field(default_factory=list)


def calculate_cpm(tasks_input: List[CpmTaskInput]) -> CpmResult:
    """
    Executes the Critical Path Method (CPM) using finish-to-start dependencies.
    
    Calculates Early Start (ES), Early Finish (EF), Late Start (LS), Late Finish (LF),
    Total Float (Slack), and identifies all critical tasks and paths.
    """
    if not tasks_input:
        return CpmResult(
            total_duration=0.0,
            critical_tasks=[],
            critical_paths=[],
            tasks={},
            warnings=["Project has no tasks."],
        )

    # 1. Validation & Graph Construction
    task_map: Dict[Any, CpmTaskInput] = {}
    successors: Dict[Any, Set[Any]] = {}
    predecessors: Dict[Any, Set[Any]] = {}
    in_degree: Dict[Any, int] = {}

    for t in tasks_input:
        if t.duration is None:
            raise InvalidDurationError(f"Task '{t.id}' is missing estimated duration.")
        if t.duration < 0.0:
            raise InvalidDurationError(f"Task '{t.id}' has negative duration ({t.duration}h).")
        
        task_map[t.id] = t
        successors[t.id] = set()
        predecessors[t.id] = set()
        in_degree[t.id] = 0

    for t in tasks_input:
        for prereq_id in t.prerequisites:
            if prereq_id == t.id:
                raise InvalidDependencyError(f"Task '{t.id}' cannot depend on itself.")
            if prereq_id not in task_map:
                raise InvalidDependencyError(
                    f"Task '{t.id}' depends on non-existent task '{prereq_id}'."
                )
            predecessors[t.id].add(prereq_id)
            successors[prereq_id].add(t.id)

    for task_id in task_map:
        in_degree[task_id] = len(predecessors[task_id])

    # 2. Topological Sort (Kahn's Algorithm with cycle detection and deterministic sorting)
    # Using sorted queue ensures deterministic ordering regardless of input sequence
    ready_queue = sorted([tid for tid, deg in in_degree.items() if deg == 0], key=str)
    topo_order: List[Any] = []

    while ready_queue:
        curr = ready_queue.pop(0)
        topo_order.append(curr)

        for succ in sorted(successors[curr], key=str):
            in_degree[succ] -= 1
            if in_degree[succ] == 0:
                ready_queue.append(succ)
        ready_queue.sort(key=str)

    if len(topo_order) != len(task_map):
        # A cycle exists. Find the cycle path for diagnostic reporting.
        cycle = _find_cycle(predecessors)
        raise CycleDetectedError(cycle)

    # 3. Forward Pass (ES & EF)
    early_start: Dict[Any, float] = {}
    early_finish: Dict[Any, float] = {}

    for tid in topo_order:
        t = task_map[tid]
        if not predecessors[tid]:
            es = 0.0
        else:
            es = max(early_finish[p] for p in predecessors[tid])
        
        ef = es + t.duration
        early_start[tid] = round(es, 4)
        early_finish[tid] = round(ef, 4)

    total_project_duration = max(early_finish.values()) if early_finish else 0.0
    total_project_duration = round(total_project_duration, 4)

    # 4. Backward Pass (LS & LF)
    late_start: Dict[Any, float] = {}
    late_finish: Dict[Any, float] = {}

    for tid in reversed(topo_order):
        t = task_map[tid]
        if not successors[tid]:
            lf = total_project_duration
        else:
            lf = min(late_start[s] for s in successors[tid])
        
        ls = lf - t.duration
        late_finish[tid] = round(lf, 4)
        late_start[tid] = round(ls, 4)

    # 5. Slack, Critical Tasks & Formatting
    task_outputs: Dict[Any, CpmTaskOutput] = {}
    critical_tasks: List[Any] = []

    for tid in sorted(topo_order, key=str):
        es = early_start[tid]
        ef = early_finish[tid]
        ls = late_start[tid]
        lf = late_finish[tid]
        slack = round(ls - es, 4)
        is_critical = abs(slack) < 1e-4

        if is_critical:
            critical_tasks.append(tid)

        t = task_map[tid]
        task_outputs[tid] = CpmTaskOutput(
            id=tid,
            title=t.title or str(tid),
            duration=t.duration,
            early_start=es,
            early_finish=ef,
            late_start=ls,
            late_finish=lf,
            slack=slack,
            is_critical=is_critical,
        )

    # 6. Critical Path Enumeration
    critical_paths = _find_critical_paths(
        topo_order=topo_order,
        predecessors=predecessors,
        successors=successors,
        early_finish=early_finish,
        early_start=early_start,
        critical_tasks=set(critical_tasks),
    )

    return CpmResult(
        total_duration=total_project_duration,
        critical_tasks=critical_tasks,
        critical_paths=critical_paths,
        tasks=task_outputs,
    )


def _find_cycle(predecessors: Dict[Any, Set[Any]]) -> List[Any]:
    """Finds an explicit cycle path using DFS for clear error diagnostics."""
    visited: Dict[Any, int] = {}  # 0=unvisited, 1=visiting, 2=visited
    parent: Dict[Any, Any] = {}

    for node in predecessors:
        visited[node] = 0

    for start_node in predecessors:
        if visited[start_node] != 0:
            continue
        
        stack = [(start_node, iter(sorted(predecessors[start_node], key=str)))]
        visited[start_node] = 1

        while stack:
            u, it = stack[-1]
            try:
                v = next(it)
                if visited[v] == 1:
                    # Cycle found from u -> v
                    cycle = [v, u]
                    curr = u
                    while curr in parent and parent[curr] != v:
                        curr = parent[curr]
                        cycle.append(curr)
                    cycle.append(v)
                    cycle.reverse()
                    return cycle
                elif visited[v] == 0:
                    visited[v] = 1
                    parent[v] = u
                    stack.append((v, iter(sorted(predecessors[v], key=str))))
            except StopIteration:
                visited[u] = 2
                stack.pop()

    return list(predecessors.keys())


def _find_critical_paths(
    topo_order: List[Any],
    predecessors: Dict[Any, Set[Any]],
    successors: Dict[Any, Set[Any]],
    early_finish: Dict[Any, float],
    early_start: Dict[Any, float],
    critical_tasks: Set[Any],
) -> List[List[Any]]:
    """
    Finds all valid critical paths from start to finish nodes consisting only of critical tasks.
    """
    if not critical_tasks:
        return []

    # Start nodes on the critical path have no critical predecessors
    start_nodes = [
        tid for tid in topo_order
        if tid in critical_tasks and not any(p in critical_tasks for p in predecessors[tid])
    ]

    all_paths: List[List[Any]] = []

    def dfs(curr: Any, path: List[Any]):
        # Check if curr is an end node on the critical path (no critical successors)
        crit_succs = [
            s for s in sorted(successors[curr], key=str)
            if s in critical_tasks and abs(early_finish[curr] - early_start[s]) < 1e-4
        ]
        
        if not crit_succs:
            all_paths.append(list(path))
            return

        for s in crit_succs:
            path.append(s)
            dfs(s, path)
            path.pop()

    for s in sorted(start_nodes, key=str):
        dfs(s, [s])

    return all_paths
