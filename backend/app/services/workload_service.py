import math
from datetime import date
from typing import Dict, List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.project import AcademicProject, ProjectMember
from app.models.task import Task, TaskAssignment
from app.models.enums import TaskStatus
from app.schemas.workload import StudentWorkloadSummary, TeamWorkloadResponse


class WorkloadService:
    """
    Computes academic team effort distribution, detects individual overloading
    and underutilization against semester thresholds, and suggests rebalancing.
    """

    @classmethod
    async def analyze_project_workload(
        cls,
        project_id: UUID,
        db: AsyncSession,
        threshold_hours: float = 25.0,
        reference_date: Optional[date] = None,
    ) -> TeamWorkloadResponse:
        ref_date = reference_date or date.today()

        # 1. Fetch team members
        members_query = await db.execute(
            select(ProjectMember)
            .options(selectinload(ProjectMember.user))
            .where(ProjectMember.project_id == project_id)
        )
        members = list(members_query.scalars().all())

        # 2. Fetch project tasks with assignments
        tasks_query = await db.execute(
            select(Task)
            .options(selectinload(Task.assignments))
            .where(Task.project_id == project_id)
        )
        tasks = list(tasks_query.scalars().all())

        # Group assignments by user
        user_tasks: Dict[UUID, List[Task]] = {m.user_id: [] for m in members}
        for t in tasks:
            for a in t.assignments:
                if a.user_id in user_tasks:
                    user_tasks[a.user_id].append(t)

        student_summaries: List[StudentWorkloadSummary] = []
        active_hours_list: List[float] = []
        overloaded_ids: List[UUID] = []
        underutilized_ids: List[UUID] = []

        for m in members:
            assigned = user_tasks[m.user_id]
            active_tasks = [t for t in assigned if t.status != TaskStatus.COMPLETED]
            completed_tasks = [t for t in assigned if t.status == TaskStatus.COMPLETED]

            active_hours = sum(float(t.estimated_duration_hours or 0.0) for t in active_tasks)
            comp_hours = sum(float(t.estimated_duration_hours or 0.0) for t in completed_tasks)

            overdue_cnt = sum(1 for t in active_tasks if t.due_date and t.due_date < ref_date)
            upcoming_cnt = len(active_tasks) - overdue_cnt

            is_overloaded = active_hours > threshold_hours
            is_underutilized = (active_hours < (threshold_hours * 0.3)) and (len(active_tasks) <= 1)

            if is_overloaded:
                overloaded_ids.append(m.user_id)
            if is_underutilized and len(members) > 1:
                underutilized_ids.append(m.user_id)

            active_hours_list.append(active_hours)

            student_summaries.append(
                StudentWorkloadSummary(
                    user_id=m.user_id,
                    full_name=m.user.full_name,
                    email=m.user.email,
                    team_role=m.team_role.value,
                    total_active_hours=round(active_hours, 1),
                    completed_hours=round(comp_hours, 1),
                    assigned_task_count=len(active_tasks),
                    overdue_task_count=overdue_cnt,
                    upcoming_task_count=upcoming_cnt,
                    completed_task_count=len(completed_tasks),
                    is_overloaded=is_overloaded,
                    is_underutilized=is_underutilized,
                )
            )

        total_team_hours = round(sum(active_hours_list), 1)
        avg_hours = round(total_team_hours / len(members), 1) if members else 0.0

        # Compute standard deviation of workload
        if len(active_hours_list) > 1:
            variance = sum((h - avg_hours) ** 2 for h in active_hours_list) / len(active_hours_list)
            std_dev = round(math.sqrt(variance), 2)
        else:
            std_dev = 0.0

        # Generate advisory recommendations
        recommendations = []
        if overloaded_ids and underutilized_ids:
            recommendations.append(
                f"Workload imbalance detected (StdDev: {std_dev}h). "
                f"{len(overloaded_ids)} member(s) exceed {threshold_hours}h while "
                f"{len(underutilized_ids)} member(s) have available capacity. "
                f"Consider reallocating upcoming non-critical tasks."
            )
        elif overloaded_ids:
            recommendations.append(
                f"{len(overloaded_ids)} member(s) exceed the semester workload threshold of {threshold_hours}h. "
                f"Review milestone scopes or extend deadlines to prevent burnout."
            )
        elif not overloaded_ids and not underutilized_ids:
            recommendations.append("Team effort is well balanced across members.")

        return TeamWorkloadResponse(
            project_id=project_id,
            threshold_hours=threshold_hours,
            reference_date=ref_date,
            total_team_active_hours=total_team_hours,
            average_hours_per_student=avg_hours,
            workload_standard_deviation=std_dev,
            student_workloads=student_summaries,
            overloaded_students=overloaded_ids,
            underutilized_students=underutilized_ids,
            recommendations=recommendations,
        )
