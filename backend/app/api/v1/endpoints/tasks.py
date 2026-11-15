from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.api.deps import get_current_user, verify_project_access
from app.models.user import User
from app.models.project import ProjectMember
from app.models.milestone import AcademicMilestone
from app.models.task import Task, TaskAssignment, TaskDependency
from app.models.enums import TaskStatus, TaskPriority, DependencyType
from app.algorithms import CpmTaskInput, calculate_cpm, CycleDetectedError
from app.schemas.task import TaskCreate, TaskUpdate, TaskRead
from app.schemas.assignment import TaskAssignmentCreate, TaskAssignmentRead
from app.schemas.dependency import TaskDependencyBase, TaskDependencyCreate, TaskDependencyRead
from app.services.notification_service import NotificationService

router = APIRouter()


@router.post("/projects/{project_id}/tasks", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
async def create_task(
    project_id: UUID,
    task_in: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Creates a new task in the specified academic project."""
    await verify_project_access(project_id, current_user, db, require_write=True)

    # Validate milestone belongs to this project
    if task_in.milestone_id:
        m_query = await db.execute(
            select(AcademicMilestone).where(
                AcademicMilestone.id == task_in.milestone_id,
                AcademicMilestone.project_id == project_id,
            )
        )
        if not m_query.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Specified milestone does not exist in this project.",
            )

    task = Task(
        project_id=project_id,
        milestone_id=task_in.milestone_id,
        title=task_in.title,
        description=task_in.description,
        status=task_in.status,
        priority=task_in.priority,
        estimated_duration_hours=task_in.estimated_duration_hours,
        actual_duration_hours=task_in.actual_duration_hours,
        start_date=task_in.start_date,
        due_date=task_in.due_date,
        created_by_id=current_user.id,
    )
    db.add(task)
    await db.commit()
    task_q = await db.execute(
        select(Task)
        .options(selectinload(Task.assignments).selectinload(TaskAssignment.user))
        .where(Task.id == task.id)
    )
    return task_q.scalar_one()


@router.get("/projects/{project_id}/tasks", response_model=List[TaskRead])
async def list_project_tasks(
    project_id: UUID,
    status_filter: Optional[TaskStatus] = Query(None, alias="status"),
    milestone_id: Optional[UUID] = Query(None),
    priority: Optional[TaskPriority] = Query(None),
    assigned_user_id: Optional[UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists project tasks with optional filtering by status, milestone, priority, or assignee."""
    await verify_project_access(project_id, current_user, db)

    query = (
        select(Task)
        .options(selectinload(Task.assignments).selectinload(TaskAssignment.user))
        .where(Task.project_id == project_id)
    )

    if status_filter:
        query = query.where(Task.status == status_filter)
    if milestone_id:
        query = query.where(Task.milestone_id == milestone_id)
    if priority:
        query = query.where(Task.priority == priority)
    if assigned_user_id:
        query = query.join(TaskAssignment, TaskAssignment.task_id == Task.id).where(
            TaskAssignment.user_id == assigned_user_id
        )

    query = query.order_by(Task.due_date, Task.created_at)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/tasks/{task_id}", response_model=TaskRead)
async def get_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves a single task by ID."""
    task_query = await db.execute(
        select(Task)
        .options(selectinload(Task.assignments).selectinload(TaskAssignment.user))
        .where(Task.id == task_id)
    )
    task = task_query.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")

    await verify_project_access(task.project_id, current_user, db)
    return task


@router.put("/tasks/{task_id}", response_model=TaskRead)
async def update_task(
    task_id: UUID,
    task_update: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Updates task attributes."""
    task_query = await db.execute(select(Task).where(Task.id == task_id))
    task = task_query.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")

    await verify_project_access(task.project_id, current_user, db, require_write=True)

    if task_update.milestone_id is not None:
        m_query = await db.execute(
            select(AcademicMilestone).where(
                AcademicMilestone.id == task_update.milestone_id,
                AcademicMilestone.project_id == task.project_id,
            )
        )
        if not m_query.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Specified milestone does not exist in this project.",
            )

    update_dict = task_update.model_dump(exclude_unset=True)
    if "status" in update_dict:
        if update_dict["status"] == TaskStatus.COMPLETED and not task.completed_at:
            task.completed_at = datetime.now(timezone.utc)
        elif update_dict["status"] != TaskStatus.COMPLETED:
            task.completed_at = None

    for field, value in update_dict.items():
        setattr(task, field, value)

    await db.commit()
    task_q = await db.execute(
        select(Task)
        .options(selectinload(Task.assignments).selectinload(TaskAssignment.user))
        .where(Task.id == task.id)
    )
    return task_q.scalar_one()


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Deletes a task from an academic project.
    Removes related task assignments and dependency edges cleanly.
    Requires write permissions for the project.
    """
    task_query = await db.execute(select(Task).where(Task.id == task_id))
    task = task_query.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")

    await verify_project_access(task.project_id, current_user, db, require_write=True)

    await db.delete(task)
    await db.commit()
    return None


@router.patch("/tasks/{task_id}/status", response_model=TaskRead)
async def update_task_status(
    task_id: UUID,
    status_value: TaskStatus,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Updates task status and manages completed_at timestamp."""
    task_query = await db.execute(select(Task).where(Task.id == task_id))
    task = task_query.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")

    await verify_project_access(task.project_id, current_user, db, require_write=True)

    task.status = status_value
    if status_value == TaskStatus.COMPLETED:
        task.completed_at = datetime.now(timezone.utc)
    else:
        task.completed_at = None

    await db.commit()
    task_q = await db.execute(
        select(Task)
        .options(selectinload(Task.assignments).selectinload(TaskAssignment.user))
        .where(Task.id == task.id)
    )
    return task_q.scalar_one()


# --- TASK ASSIGNMENTS ---

@router.post("/tasks/{task_id}/assignments", response_model=TaskAssignmentRead, status_code=status.HTTP_201_CREATED)
async def assign_task_member(
    task_id: UUID,
    assignment_in: TaskAssignmentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Assigns an eligible project team member to a task."""
    task_query = await db.execute(select(Task).where(Task.id == task_id))
    task = task_query.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")

    await verify_project_access(task.project_id, current_user, db, require_write=True)

    # Validate assignee is a member of the project
    mem_query = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == task.project_id,
            ProjectMember.user_id == assignment_in.user_id,
        )
    )
    if not mem_query.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot assign task: User is not a registered member of this project.",
        )

    # Check if already assigned
    existing_query = await db.execute(
        select(TaskAssignment).where(
            TaskAssignment.task_id == task_id,
            TaskAssignment.user_id == assignment_in.user_id,
        )
    )
    if existing_query.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already assigned to this task.",
        )

    assignment = TaskAssignment(
        task_id=task_id,
        user_id=assignment_in.user_id,
        assigned_by_id=current_user.id,
    )
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)

    # Notify newly assigned student
    await NotificationService.notify_task_assignment(
        db=db,
        task=task,
        recipient_id=assignment_in.user_id,
        assigner=current_user,
    )

    q = await db.execute(
        select(TaskAssignment)
        .options(selectinload(TaskAssignment.user))
        .where(TaskAssignment.id == assignment.id)
    )
    return q.scalar_one()


@router.delete("/tasks/{task_id}/assignments/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unassign_task_member(
    task_id: UUID,
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Unassigns a student from a task."""
    task_query = await db.execute(select(Task).where(Task.id == task_id))
    task = task_query.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")

    await verify_project_access(task.project_id, current_user, db, require_write=True)

    del_res = await db.execute(
        delete(TaskAssignment).where(
            TaskAssignment.task_id == task_id,
            TaskAssignment.user_id == user_id,
        )
    )
    if del_res.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found.")

    await db.commit()
    return None


@router.get("/tasks/{task_id}/assignments", response_model=List[TaskAssignmentRead])
async def list_task_assignments(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists all assigned members for a given task."""
    task_query = await db.execute(select(Task).where(Task.id == task_id))
    task = task_query.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")

    await verify_project_access(task.project_id, current_user, db)

    res = await db.execute(
        select(TaskAssignment)
        .options(selectinload(TaskAssignment.user))
        .where(TaskAssignment.task_id == task_id)
        .order_by(TaskAssignment.assigned_at)
    )
    return list(res.scalars().all())


# --- TASK DEPENDENCIES ---

@router.post("/tasks/{task_id}/dependencies", response_model=TaskDependencyRead, status_code=status.HTTP_201_CREATED)
async def add_task_dependency(
    task_id: UUID,
    dep_in: TaskDependencyBase,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Adds a prerequisite dependency edge (task_id depends on depends_on_task_id).
    Validates:
    - No self-dependency
    - Both tasks belong to the same project
    - Adding edge will not create a dependency cycle
    """
    if task_id == dep_in.depends_on_task_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A task cannot depend on itself (self-dependency prohibited).",
        )

    # Fetch both tasks
    tasks_query = await db.execute(
        select(Task).where(Task.id.in_([task_id, dep_in.depends_on_task_id]))
    )
    tasks = {t.id: t for t in tasks_query.scalars().all()}

    if task_id not in tasks:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dependent task not found.")
    if dep_in.depends_on_task_id not in tasks:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prerequisite task not found.")

    t_dependent = tasks[task_id]
    t_prereq = tasks[dep_in.depends_on_task_id]

    if t_dependent.project_id != t_prereq.project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cross-project dependencies are not allowed. Both tasks must belong to the same project.",
        )

    project_id = t_dependent.project_id
    await verify_project_access(project_id, current_user, db, require_write=True)

    # Check if duplicate dependency
    dup_query = await db.execute(
        select(TaskDependency).where(
            TaskDependency.task_id == task_id,
            TaskDependency.depends_on_task_id == dep_in.depends_on_task_id,
        )
    )
    if dup_query.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This dependency already exists.",
        )

    # Cycle Detection check: Fetch all existing dependencies in project
    all_tasks_query = await db.execute(select(Task).where(Task.project_id == project_id))
    all_tasks = list(all_tasks_query.scalars().all())
    task_ids = [t.id for t in all_tasks]

    all_deps_query = await db.execute(
        select(TaskDependency).where(TaskDependency.task_id.in_(task_ids))
    )
    all_deps = list(all_deps_query.scalars().all())

    # Build graph with proposed edge
    prereqs = {t.id: set() for t in all_tasks}
    for d in all_deps:
        prereqs[d.task_id].add(d.depends_on_task_id)
    prereqs[task_id].add(dep_in.depends_on_task_id)

    cpm_inputs = [
        CpmTaskInput(id=t.id, duration=float(t.estimated_duration_hours or 0.0), prerequisites=prereqs[t.id])
        for t in all_tasks
    ]

    try:
        calculate_cpm(cpm_inputs)
    except CycleDetectedError as exc:
        raise HTTPException(
            status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
            detail=f"Cannot add dependency: {str(exc)}",
        )

    dependency = TaskDependency(
        task_id=task_id,
        depends_on_task_id=dep_in.depends_on_task_id,
        dependency_type=dep_in.dependency_type,
    )
    db.add(dependency)
    await db.commit()
    await db.refresh(dependency)
    return dependency


@router.delete("/tasks/{task_id}/dependencies/{depends_on_task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_task_dependency(
    task_id: UUID,
    depends_on_task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Removes a prerequisite dependency edge."""
    task_query = await db.execute(select(Task).where(Task.id == task_id))
    task = task_query.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")

    await verify_project_access(task.project_id, current_user, db, require_write=True)

    del_res = await db.execute(
        delete(TaskDependency).where(
            TaskDependency.task_id == task_id,
            TaskDependency.depends_on_task_id == depends_on_task_id,
        )
    )
    if del_res.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dependency not found.")

    await db.commit()
    return None
