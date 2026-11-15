import pytest
import random
from app.algorithms.cpm import CpmTaskInput, calculate_cpm
from app.algorithms.exceptions import (
    CycleDetectedError,
    InvalidDependencyError,
    InvalidDurationError,
)


def test_cpm_linear_project():
    """
    Tests linear graph: A (3h) -> B (4h) -> C (2h).
    Total duration = 9h. All tasks are critical.
    """
    tasks = [
        CpmTaskInput(id="A", duration=3.0, prerequisites=set()),
        CpmTaskInput(id="B", duration=4.0, prerequisites={"A"}),
        CpmTaskInput(id="C", duration=2.0, prerequisites={"B"}),
    ]
    res = calculate_cpm(tasks)

    assert res.total_duration == 9.0
    assert set(res.critical_tasks) == {"A", "B", "C"}
    assert res.critical_paths == [["A", "B", "C"]]

    # Verify Task A
    assert res.tasks["A"].early_start == 0.0
    assert res.tasks["A"].early_finish == 3.0
    assert res.tasks["A"].late_start == 0.0
    assert res.tasks["A"].late_finish == 3.0
    assert res.tasks["A"].slack == 0.0
    assert res.tasks["A"].is_critical is True

    # Verify Task B
    assert res.tasks["B"].early_start == 3.0
    assert res.tasks["B"].early_finish == 7.0
    assert res.tasks["B"].late_start == 3.0
    assert res.tasks["B"].late_finish == 7.0
    assert res.tasks["B"].slack == 0.0
    assert res.tasks["B"].is_critical is True

    # Verify Task C
    assert res.tasks["C"].early_start == 7.0
    assert res.tasks["C"].early_finish == 9.0
    assert res.tasks["C"].late_start == 7.0
    assert res.tasks["C"].late_finish == 9.0
    assert res.tasks["C"].slack == 0.0
    assert res.tasks["C"].is_critical is True


def test_cpm_parallel_branches_and_slack():
    """
    Diamond graph:
      Start (2h) -> Branch1 (5h) -> End (3h)
      Start (2h) -> Branch2 (2h) -> End (3h)
    Critical path: Start -> Branch1 -> End (total 10h).
    Branch2 should have slack = 3h.
    """
    tasks = [
        CpmTaskInput(id="Start", duration=2.0),
        CpmTaskInput(id="Branch1", duration=5.0, prerequisites={"Start"}),
        CpmTaskInput(id="Branch2", duration=2.0, prerequisites={"Start"}),
        CpmTaskInput(id="End", duration=3.0, prerequisites={"Branch1", "Branch2"}),
    ]
    res = calculate_cpm(tasks)

    assert res.total_duration == 10.0
    assert set(res.critical_tasks) == {"Start", "Branch1", "End"}
    assert res.critical_paths == [["Start", "Branch1", "End"]]

    # Branch2 has 3 hours of slack
    b2 = res.tasks["Branch2"]
    assert b2.is_critical is False
    assert b2.early_start == 2.0
    assert b2.early_finish == 4.0
    assert b2.late_start == 5.0
    assert b2.late_finish == 7.0
    assert b2.slack == 3.0


def test_cpm_multiple_start_and_end_tasks():
    """
    Multiple roots (S1, S2) and multiple leaves (E1, E2):
      S1 (3h) -> Mid (4h) -> E1 (2h)
      S2 (5h) -> Mid (4h) -> E2 (6h)
    Longest path: S2 (5) -> Mid (4) -> E2 (6) = 15h
    """
    tasks = [
        CpmTaskInput(id="S1", duration=3.0),
        CpmTaskInput(id="S2", duration=5.0),
        CpmTaskInput(id="Mid", duration=4.0, prerequisites={"S1", "S2"}),
        CpmTaskInput(id="E1", duration=2.0, prerequisites={"Mid"}),
        CpmTaskInput(id="E2", duration=6.0, prerequisites={"Mid"}),
    ]
    res = calculate_cpm(tasks)

    assert res.total_duration == 15.0
    assert set(res.critical_tasks) == {"S2", "Mid", "E2"}
    assert res.critical_paths == [["S2", "Mid", "E2"]]
    assert res.tasks["S1"].slack == 2.0
    assert res.tasks["E1"].slack == 4.0


def test_cpm_zero_duration_milestone():
    """Milestones with zero duration should be supported cleanly."""
    tasks = [
        CpmTaskInput(id="M0", duration=0.0),
        CpmTaskInput(id="TaskA", duration=5.0, prerequisites={"M0"}),
        CpmTaskInput(id="M1", duration=0.0, prerequisites={"TaskA"}),
    ]
    res = calculate_cpm(tasks)
    assert res.total_duration == 5.0
    assert set(res.critical_tasks) == {"M0", "TaskA", "M1"}


def test_cpm_empty_project():
    res = calculate_cpm([])
    assert res.total_duration == 0.0
    assert res.critical_tasks == []
    assert len(res.warnings) > 0


def test_cpm_invalid_duration_errors():
    with pytest.raises(InvalidDurationError):
        calculate_cpm([CpmTaskInput(id="A", duration=-1.0)])

    with pytest.raises(InvalidDurationError):
        calculate_cpm([CpmTaskInput(id="A", duration=None)])  # type: ignore


def test_cpm_self_dependency():
    with pytest.raises(InvalidDependencyError) as exc_info:
        calculate_cpm([CpmTaskInput(id="A", duration=2.0, prerequisites={"A"})])
    assert "cannot depend on itself" in str(exc_info.value)


def test_cpm_missing_dependency():
    with pytest.raises(InvalidDependencyError) as exc_info:
        calculate_cpm([CpmTaskInput(id="A", duration=2.0, prerequisites={"UNKNOWN"})])
    assert "non-existent task" in str(exc_info.value)


def test_cpm_cycle_detection():
    # A -> B -> C -> A
    tasks = [
        CpmTaskInput(id="A", duration=2.0, prerequisites={"C"}),
        CpmTaskInput(id="B", duration=3.0, prerequisites={"A"}),
        CpmTaskInput(id="C", duration=1.0, prerequisites={"B"}),
    ]
    with pytest.raises(CycleDetectedError) as exc_info:
        calculate_cpm(tasks)
    assert "Dependency cycle detected" in str(exc_info.value)


def test_cpm_deterministic_ordering():
    """Ensures CPM results are identical regardless of list ordering."""
    base_tasks = [
        CpmTaskInput(id=f"T{i}", duration=float(i + 1), prerequisites={f"T{i-1}"} if i > 0 else set())
        for i in range(8)
    ]
    res1 = calculate_cpm(base_tasks)

    for seed in range(5):
        shuffled = list(base_tasks)
        random.seed(seed)
        random.shuffle(shuffled)
        res2 = calculate_cpm(shuffled)
        assert res1.total_duration == res2.total_duration
        assert res1.critical_tasks == res2.critical_tasks
        assert res1.critical_paths == res2.critical_paths


def test_cpm_dual_critical_paths_parallel_tasks():
    """
    Tests parallel branches with identical durations:
      Requirement Analysis (4h) -> System Design (6h)
      System Design (6h) -> Backend Implementation (10h)
      System Design (6h) -> Frontend Implementation (10h)
      Backend & Frontend -> Integration Testing (4h)
      Integration Testing -> Documentation (5h)

    Total project duration = 4 + 6 + 10 + 4 + 5 = 29.0h (NOT 39.0h).
    Both parallel branches take 10.0h, so both are critical with 0 slack (2 critical paths).
    Integration testing waits for both branches and starts at hour 20.0.
    """
    tasks = [
        CpmTaskInput(id="req", title="Requirement Analysis", duration=4.0),
        CpmTaskInput(id="design", title="System Design", duration=6.0, prerequisites={"req"}),
        CpmTaskInput(id="backend", title="Backend Implementation", duration=10.0, prerequisites={"design"}),
        CpmTaskInput(id="frontend", title="Frontend Implementation", duration=10.0, prerequisites={"design"}),
        CpmTaskInput(id="testing", title="Integration Testing", duration=4.0, prerequisites={"backend", "frontend"}),
        CpmTaskInput(id="doc", title="Documentation", duration=5.0, prerequisites={"testing"}),
    ]
    res = calculate_cpm(tasks)

    assert res.total_duration == 29.0
    assert len(res.critical_tasks) == 6
    assert set(res.critical_tasks) == {"req", "design", "backend", "frontend", "testing", "doc"}
    assert len(res.critical_paths) == 2
    assert ["req", "design", "backend", "testing", "doc"] in res.critical_paths
    assert ["req", "design", "frontend", "testing", "doc"] in res.critical_paths

    # Requirement Analysis
    assert res.tasks["req"].early_start == 0.0
    assert res.tasks["req"].early_finish == 4.0
    assert res.tasks["req"].slack == 0.0
    assert res.tasks["req"].is_critical is True

    # System Design
    assert res.tasks["design"].early_start == 4.0
    assert res.tasks["design"].early_finish == 10.0
    assert res.tasks["design"].slack == 0.0
    assert res.tasks["design"].is_critical is True

    # Parallel branches: both start at 10.0 and finish at 20.0
    assert res.tasks["backend"].early_start == 10.0
    assert res.tasks["backend"].early_finish == 20.0
    assert res.tasks["backend"].late_start == 10.0
    assert res.tasks["backend"].late_finish == 20.0
    assert res.tasks["backend"].slack == 0.0
    assert res.tasks["backend"].is_critical is True

    assert res.tasks["frontend"].early_start == 10.0
    assert res.tasks["frontend"].early_finish == 20.0
    assert res.tasks["frontend"].late_start == 10.0
    assert res.tasks["frontend"].late_finish == 20.0
    assert res.tasks["frontend"].slack == 0.0
    assert res.tasks["frontend"].is_critical is True

    # Integration Testing waits for both parallel branches: ES = max(20.0, 20.0) = 20.0
    assert res.tasks["testing"].early_start == 20.0
    assert res.tasks["testing"].early_finish == 24.0
    assert res.tasks["testing"].slack == 0.0
    assert res.tasks["testing"].is_critical is True

    # Documentation
    assert res.tasks["doc"].early_start == 24.0
    assert res.tasks["doc"].early_finish == 29.0
    assert res.tasks["doc"].slack == 0.0
    assert res.tasks["doc"].is_critical is True


def test_cpm_parallel_tasks_with_unequal_durations_and_non_critical_slack():
    """
    Tests parallel branches with unequal durations:
      Backend Implementation = 10.0h (Critical)
      Frontend Implementation = 8.0h (Non-critical, slack = 2.0h)
    
    Total duration = 4 + 6 + 10 + 4 + 5 = 29.0h.
    Frontend has ES=10.0, EF=18.0, LS=12.0, LF=20.0, slack = 2.0h -> is_critical = False.
    """
    tasks = [
        CpmTaskInput(id="req", title="Requirement Analysis", duration=4.0),
        CpmTaskInput(id="design", title="System Design", duration=6.0, prerequisites={"req"}),
        CpmTaskInput(id="backend", title="Backend Implementation", duration=10.0, prerequisites={"design"}),
        CpmTaskInput(id="frontend", title="Frontend Implementation", duration=8.0, prerequisites={"design"}),
        CpmTaskInput(id="testing", title="Integration Testing", duration=4.0, prerequisites={"backend", "frontend"}),
        CpmTaskInput(id="doc", title="Documentation", duration=5.0, prerequisites={"testing"}),
    ]
    res = calculate_cpm(tasks)

    assert res.total_duration == 29.0
    assert len(res.critical_tasks) == 5
    assert set(res.critical_tasks) == {"req", "design", "backend", "testing", "doc"}
    assert res.critical_paths == [["req", "design", "backend", "testing", "doc"]]

    # Frontend is non-critical with 2h slack
    fe = res.tasks["frontend"]
    assert fe.is_critical is False
    assert fe.early_start == 10.0
    assert fe.early_finish == 18.0
    assert fe.late_start == 12.0
    assert fe.late_finish == 20.0
    assert fe.slack == 2.0

    # Backend is critical with 0h slack
    be = res.tasks["backend"]
    assert be.is_critical is True
    assert be.early_start == 10.0
    assert be.early_finish == 20.0
    assert be.slack == 0.0

    # Integration testing waits for both, ES = max(20.0, 18.0) = 20.0
    test = res.tasks["testing"]
    assert test.early_start == 20.0
    assert test.early_finish == 24.0
    assert test.is_critical is True


def test_cpm_sequential_erroneous_edge_comparison():
    """
    Directly compares:
    1. Erroneous serialized graph (with Backend -> Frontend): duration = 39.0h, 1 critical path.
    2. Corrected parallel graph (without Backend -> Frontend): duration = 29.0h, 2 critical paths.
    """
    # 1. Erroneous (sequential)
    erroneous_tasks = [
        CpmTaskInput(id="req", duration=4.0),
        CpmTaskInput(id="design", duration=6.0, prerequisites={"req"}),
        CpmTaskInput(id="backend", duration=10.0, prerequisites={"design"}),
        CpmTaskInput(id="frontend", duration=10.0, prerequisites={"design", "backend"}),  # Erroneous edge!
        CpmTaskInput(id="testing", duration=4.0, prerequisites={"backend", "frontend"}),
        CpmTaskInput(id="doc", duration=5.0, prerequisites={"testing"}),
    ]
    err_res = calculate_cpm(erroneous_tasks)
    assert err_res.total_duration == 39.0
    assert len(err_res.critical_tasks) == 6
    assert err_res.tasks["frontend"].early_start == 20.0
    assert err_res.tasks["frontend"].early_finish == 30.0
    assert err_res.tasks["testing"].early_start == 30.0

    # 2. Corrected (parallel)
    corrected_tasks = [
        CpmTaskInput(id="req", duration=4.0),
        CpmTaskInput(id="design", duration=6.0, prerequisites={"req"}),
        CpmTaskInput(id="backend", duration=10.0, prerequisites={"design"}),
        CpmTaskInput(id="frontend", duration=10.0, prerequisites={"design"}),  # Correct parallel prerequisite
        CpmTaskInput(id="testing", duration=4.0, prerequisites={"backend", "frontend"}),
        CpmTaskInput(id="doc", duration=5.0, prerequisites={"testing"}),
    ]
    corr_res = calculate_cpm(corrected_tasks)
    assert corr_res.total_duration == 29.0
    assert corr_res.tasks["backend"].early_start == 10.0
    assert corr_res.tasks["frontend"].early_start == 10.0
    assert corr_res.tasks["testing"].early_start == 20.0
