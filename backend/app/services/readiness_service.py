from datetime import date, datetime, timezone
from typing import Dict, List, Optional, Set
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.project import AcademicProject
from app.models.milestone import AcademicMilestone
from app.models.task import Task, TaskDependency
from app.models.review import ProjectReview
from app.models.enums import MilestoneStatus, TaskStatus, ReviewStatus
from app.algorithms import CpmTaskInput, calculate_cpm
from app.schemas.readiness import ReadinessBreakdown, ReviewReadinessResponse


class ReadinessService:
    """
    Evaluates project readiness for faculty reviews and viva defenses using
    a transparent multi-dimensional scoring model.
    """

    @classmethod
    async def evaluate_readiness(
        cls,
        project_id: UUID,
        db: AsyncSession,
        reference_date: Optional[date] = None,
    ) -> ReviewReadinessResponse:
        ref_date = reference_date or date.today()

        # 1. Fetch Milestones
        m_query = await db.execute(
            select(AcademicMilestone)
            .where(AcademicMilestone.project_id == project_id)
            .order_by(AcademicMilestone.sequence_number)
        )
        milestones = list(m_query.scalars().all())

        # 2. Fetch Tasks & Dependencies
        t_query = await db.execute(
            select(Task)
            .where(Task.project_id == project_id)
        )
        tasks = list(t_query.scalars().all())

        task_ids = [t.id for t in tasks]
        d_query = await db.execute(
            select(TaskDependency).where(TaskDependency.task_id.in_(task_ids))
        )
        dependencies = list(d_query.scalars().all())

        # 3. Fetch Next Scheduled Review
        now_dt = datetime.now(timezone.utc)
        r_query = await db.execute(
            select(ProjectReview)
            .where(
                ProjectReview.project_id == project_id,
                ProjectReview.status == ReviewStatus.SCHEDULED,
            )
            .order_by(ProjectReview.scheduled_at)
        )
        next_review = r_query.scalars().first()

        blockers: List[str] = []
        recommendations: List[str] = []

        # Check for insufficient data
        if not milestones and not tasks:
            return ReviewReadinessResponse(
                project_id=project_id,
                readiness_score=0.0,
                readiness_level="INSUFFICIENT_DATA",
                score_breakdown=ReadinessBreakdown(
                    milestone_score=0.0,
                    task_completion_score=0.0,
                    critical_path_score=0.0,
                    overdue_score=0.0,
                    review_timing_score=0.0,
                    total_score=0.0,
                ),
                blockers=["Project contains no milestones or tasks."],
                actionable_recommendations=["Define academic milestones and initial work breakdown tasks."],
                next_review_scheduled_at=next_review.scheduled_at if next_review else None,
            )

        # Dimension 1: Milestone Score (Max 40 pts)
        req_milestones = [m for m in milestones if m.is_required]
        if req_milestones:
            def is_milestone_completed(m: AcademicMilestone) -> bool:
                st = getattr(m, "status", None)
                if st is None:
                    return False
                if isinstance(st, str):
                    return st.lower() == "completed"
                return st == MilestoneStatus.COMPLETED

            completed_m = [m for m in req_milestones if is_milestone_completed(m)]
            milestone_ratio = len(completed_m) / len(req_milestones)
            milestone_score = round(40.0 * milestone_ratio, 1)

            overdue_m = [
                m for m in req_milestones
                if not is_milestone_completed(m) and m.planned_date < ref_date
            ]
            for om in overdue_m:
                blockers.append(f"Required milestone '{om.title}' is overdue (planned: {om.planned_date}).")
        else:
            milestone_score = 20.0  # Neutral if no required milestones specified
            recommendations.append("Set required milestone checkpoints to improve review readiness tracking.")

        # Dimension 2 & 3: Task Completion (15 pts) & Critical Path Health (15 pts)
        if tasks:
            completed_tasks = [t for t in tasks if t.status == TaskStatus.COMPLETED]
            task_ratio = len(completed_tasks) / len(tasks)
            task_comp_score = round(15.0 * task_ratio, 1)

            # Compute CPM for critical path health
            prereqs: Dict[UUID, Set[UUID]] = {t.id: set() for t in tasks}
            for d in dependencies:
                if d.depends_on_task_id in prereqs:
                    prereqs[d.task_id].add(d.depends_on_task_id)

            cpm_inputs = [
                CpmTaskInput(id=t.id, duration=float(t.estimated_duration_hours or 0.0), prerequisites=prereqs[t.id])
                for t in tasks
            ]

            try:
                cpm_res = calculate_cpm(cpm_inputs)
                crit_ids = set(cpm_res.critical_tasks)
                crit_tasks = [t for t in tasks if t.id in crit_ids]
                if crit_tasks:
                    completed_crit = [t for t in crit_tasks if t.status == TaskStatus.COMPLETED]
                    crit_ratio = len(completed_crit) / len(crit_tasks)
                    crit_score = round(15.0 * crit_ratio, 1)

                    overdue_crit = [t for t in crit_tasks if t.status != TaskStatus.COMPLETED and t.due_date and t.due_date < ref_date]
                    for oct in overdue_crit:
                        blockers.append(f"Critical path task '{oct.title}' is overdue (due: {oct.due_date}).")
                else:
                    crit_score = 15.0
            except Exception:
                crit_score = 7.5
                blockers.append("Dependency cycle detected; critical path health compromised.")
        else:
            task_comp_score = 0.0
            crit_score = 0.0

        # Dimension 4: Overdue Tasks Penalty (Max 20 pts, -5 pts per active overdue task)
        active_overdue = [
            t for t in tasks
            if t.status != TaskStatus.COMPLETED and t.due_date and t.due_date < ref_date
        ]
        overdue_score = max(0.0, round(20.0 - 5.0 * len(active_overdue), 1))
        if active_overdue:
            recommendations.append(f"{len(active_overdue)} active task(s) are overdue. Prioritize completing them.")

        # Dimension 5: Upcoming Review Timing Score (Max 10 pts)
        if next_review:
            days_to_rev = (next_review.scheduled_at.date() - ref_date).days
            if days_to_rev <= 7:
                # If review within 7 days, check readiness
                if len(blockers) == 0 and milestone_score >= 30.0:
                    review_score = 10.0
                elif len(blockers) > 0:
                    review_score = 3.0
                    recommendations.append(f"Faculty review scheduled in {days_to_rev} day(s) with {len(blockers)} active blocker(s).")
                else:
                    review_score = 6.0
            else:
                review_score = 10.0
        else:
            review_score = 10.0

        total_score = round(
            milestone_score + task_comp_score + crit_score + overdue_score + review_score,
            1,
        )

        if total_score >= 80.0 and not blockers:
            level = "EXCELLENT / VIVA READY"
        elif total_score >= 60.0:
            level = "GOOD / ON TRACK"
        elif total_score >= 40.0:
            level = "NEEDS ATTENTION"
        else:
            level = "CRITICAL BLOCKED"

        if not recommendations and not blockers:
            recommendations.append("Project is on track for upcoming academic evaluations.")

        return ReviewReadinessResponse(
            project_id=project_id,
            readiness_score=total_score,
            readiness_level=level,
            score_breakdown=ReadinessBreakdown(
                milestone_score=milestone_score,
                task_completion_score=task_comp_score,
                critical_path_score=crit_score,
                overdue_score=overdue_score,
                review_timing_score=review_score,
                total_score=total_score,
            ),
            blockers=blockers,
            actionable_recommendations=recommendations,
            next_review_scheduled_at=next_review.scheduled_at if next_review else None,
        )
