import pytest
from datetime import date, timedelta
from app.algorithms.priority_scheduling import (
    PriorityTaskInput,
    PriorityWeights,
    compute_priority_schedule,
)
from app.models.enums import TaskPriority, TaskStatus
from app.algorithms.exceptions import CycleDetectedError


def test_priority_ranking_by_priority_level():
    ref = date(2026, 3, 1)
    tasks = [
        PriorityTaskInput(id="T_LOW", title="Low", status=TaskStatus.TODO, priority=TaskPriority.LOW, due_date=ref + timedelta(days=10)),
        PriorityTaskInput(id="T_CRIT", title="Crit", status=TaskStatus.TODO, priority=TaskPriority.CRITICAL, due_date=ref + timedelta(days=10)),
        PriorityTaskInput(id="T_MED", title="Med", status=TaskStatus.TODO, priority=TaskPriority.MEDIUM, due_date=ref + timedelta(days=10)),
        PriorityTaskInput(id="T_HIGH", title="High", status=TaskStatus.TODO, priority=TaskPriority.HIGH, due_date=ref + timedelta(days=10)),
    ]
    res = compute_priority_schedule(tasks, reference_date=ref)
    recommended_ids = [t.id for t in res.recommended_tasks]
    assert recommended_ids == ["T_CRIT", "T_HIGH", "T_MED", "T_LOW"]


def test_priority_deadline_urgency_factor():
    ref = date(2026, 3, 1)
    tasks = [
        # Same priority, different deadlines
        PriorityTaskInput(id="Far", title="Far", status=TaskStatus.TODO, priority=TaskPriority.HIGH, due_date=ref + timedelta(days=40)),
        PriorityTaskInput(id="Imminent", title="Imminent", status=TaskStatus.TODO, priority=TaskPriority.HIGH, due_date=ref + timedelta(days=2)),
        PriorityTaskInput(id="Overdue", title="Overdue", status=TaskStatus.TODO, priority=TaskPriority.HIGH, due_date=ref - timedelta(days=1)),
    ]
    res = compute_priority_schedule(tasks, reference_date=ref)
    recommended_ids = [t.id for t in res.recommended_tasks]
    # Overdue should have the highest urgency, followed by Imminent, then Far
    assert recommended_ids[0] == "Overdue"
    assert recommended_ids[1] == "Imminent"
    assert recommended_ids[2] == "Far"


def test_priority_critical_path_and_downstream_bonus():
    ref = date(2026, 3, 1)
    # T_Normal vs T_CritPath (same priority and due date)
    tasks = [
        PriorityTaskInput(id="T_Normal", title="Normal", status=TaskStatus.TODO, priority=TaskPriority.MEDIUM, due_date=ref + timedelta(days=5), is_critical=False),
        PriorityTaskInput(id="T_Crit", title="Critical", status=TaskStatus.TODO, priority=TaskPriority.MEDIUM, due_date=ref + timedelta(days=5), is_critical=True),
    ]
    res = compute_priority_schedule(tasks, reference_date=ref)
    assert res.recommended_tasks[0].id == "T_Crit"
    assert res.recommended_tasks[0].total_score > res.recommended_tasks[1].total_score


def test_priority_eligibility_and_blocked_tasks():
    """
    Prerequisite A -> Dependent B
    If A is TODO, B is BLOCKED and not in the recommended queue.
    If A is COMPLETED, B becomes ELIGIBLE and enters the recommended queue.
    """
    ref = date(2026, 3, 1)
    tasks = [
        PriorityTaskInput(id="A", title="Prereq A", status=TaskStatus.TODO, priority=TaskPriority.HIGH),
        PriorityTaskInput(id="B", title="Dependent B", status=TaskStatus.TODO, priority=TaskPriority.CRITICAL, prerequisites={"A"}),
    ]
    res = compute_priority_schedule(tasks, reference_date=ref)

    # A is recommended, B is blocked
    assert [t.id for t in res.recommended_tasks] == ["A"]
    assert [t.id for t in res.blocked_tasks] == ["B"]
    assert res.blocked_tasks[0].is_eligible is False
    assert res.blocked_tasks[0].blocking_prerequisites == ["A"]

    # Now mark A as completed
    tasks[0].status = TaskStatus.COMPLETED
    res2 = compute_priority_schedule(tasks, reference_date=ref)

    # B is now eligible and recommended; A is in completed queue
    assert [t.id for t in res2.recommended_tasks] == ["B"]
    assert [t.id for t in res2.completed_tasks] == ["A"]
    assert len(res2.blocked_tasks) == 0


def test_priority_deterministic_tie_breaking():
    ref = date(2026, 3, 1)
    # Identical priority, due date, duration
    tasks = [
        PriorityTaskInput(id="Task_Z", title="Z", status=TaskStatus.TODO, priority=TaskPriority.MEDIUM, due_date=ref + timedelta(days=5)),
        PriorityTaskInput(id="Task_A", title="A", status=TaskStatus.TODO, priority=TaskPriority.MEDIUM, due_date=ref + timedelta(days=5)),
        PriorityTaskInput(id="Task_M", title="M", status=TaskStatus.TODO, priority=TaskPriority.MEDIUM, due_date=ref + timedelta(days=5)),
    ]
    res1 = compute_priority_schedule(tasks, reference_date=ref)
    res2 = compute_priority_schedule(list(reversed(tasks)), reference_date=ref)

    # By tie-breaking, Task_A < Task_M < Task_Z
    order1 = [t.id for t in res1.recommended_tasks]
    order2 = [t.id for t in res2.recommended_tasks]
    assert order1 == ["Task_A", "Task_M", "Task_Z"]
    assert order1 == order2


def test_priority_cycle_detection():
    tasks = [
        PriorityTaskInput(id="A", title="A", status=TaskStatus.TODO, priority=TaskPriority.HIGH, prerequisites={"B"}),
        PriorityTaskInput(id="B", title="B", status=TaskStatus.TODO, priority=TaskPriority.HIGH, prerequisites={"A"}),
    ]
    with pytest.raises(CycleDetectedError):
        compute_priority_schedule(tasks)
