import uuid
from datetime import date
from typing import Dict, List, Optional, Set
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.project import AcademicProject
from app.models.task import Task, TaskDependency
from app.algorithms import (
    CpmTaskInput,
    calculate_cpm,
    PertTaskEstimate,
    analyze_pert,
    PriorityTaskInput,
    PriorityWeights,
    compute_priority_schedule,
    CycleDetectedError,
    InvalidDependencyError,
    InvalidDurationError,
    InvalidPertEstimateError,
)
from app.schemas.scheduling import (
    CpmAnalysisResponse,
    CpmTaskMetric,
    PertCalculationRequest,
    PertAnalysisResponse,
    PertTaskMetric,
    PriorityScheduleResponse,
    PriorityTaskOutputSchema,
    ScoreBreakdownSchema,
)


class SchedulingService:
    """
    Translates database models and queries into algorithm inputs,
    executes pure scheduling algorithms, and returns typed response schemas.
    """

    @staticmethod
    async def get_project_tasks_and_dependencies(
        project_id: UUID,
        db: AsyncSession,
    ) -> tuple[AcademicProject, List[Task], List[TaskDependency]]:
        """Fetches project, tasks, and task dependencies scoped to the project."""
        # 1. Verify project exists
        proj_query = await db.execute(
            select(AcademicProject).where(AcademicProject.id == project_id)
        )
        project = proj_query.scalar_one_or_none()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID '{project_id}' not found.",
            )

        # 2. Fetch all tasks for this project
        tasks_query = await db.execute(
            select(Task)
            .where(Task.project_id == project_id)
            .order_by(Task.created_at)
        )
        tasks = list(tasks_query.scalars().all())

        if not tasks:
            return project, [], []

        task_ids = [t.id for t in tasks]

        # 3. Fetch dependencies connecting these tasks
        deps_query = await db.execute(
            select(TaskDependency)
            .where(TaskDependency.task_id.in_(task_ids))
        )
        dependencies = list(deps_query.scalars().all())

        return project, tasks, dependencies

    @classmethod
    async def calculate_project_cpm(
        cls,
        project_id: UUID,
        db: AsyncSession,
    ) -> CpmAnalysisResponse:
        """Runs the Critical Path Method for all tasks in the project."""
        project, tasks, dependencies = await cls.get_project_tasks_and_dependencies(project_id, db)

        if not tasks:
            return CpmAnalysisResponse(
                project_id=project_id,
                total_project_duration_hours=0.0,
                critical_tasks=[],
                critical_paths=[],
                tasks={},
                warnings=["Project currently contains no tasks."],
            )

        # Build task prerequisites mapping
        prereqs: Dict[UUID, Set[UUID]] = {t.id: set() for t in tasks}
        for d in dependencies:
            if d.depends_on_task_id in prereqs:
                prereqs[d.task_id].add(d.depends_on_task_id)

        cpm_inputs = [
            CpmTaskInput(
                id=t.id,
                duration=float(t.estimated_duration_hours),
                prerequisites=prereqs[t.id],
                title=t.title,
            )
            for t in tasks
        ]

        try:
            cpm_result = calculate_cpm(cpm_inputs)
        except (CycleDetectedError, InvalidDependencyError, InvalidDurationError) as exc:
            raise HTTPException(
                status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
                detail=str(exc),
            )

        task_metrics: Dict[str, CpmTaskMetric] = {}
        for tid, out in cpm_result.tasks.items():
            task_metrics[str(tid)] = CpmTaskMetric(
                id=tid,
                title=out.title,
                duration=out.duration,
                early_start=out.early_start,
                early_finish=out.early_finish,
                late_start=out.late_start,
                late_finish=out.late_finish,
                slack=out.slack,
                is_critical=out.is_critical,
            )

        return CpmAnalysisResponse(
            project_id=project_id,
            total_project_duration_hours=cpm_result.total_duration,
            critical_tasks=cpm_result.critical_tasks,
            critical_paths=cpm_result.critical_paths,
            tasks=task_metrics,
            warnings=cpm_result.warnings,
        )

    @classmethod
    async def calculate_project_priority_schedule(
        cls,
        project_id: UUID,
        db: AsyncSession,
        reference_date: Optional[date] = None,
        weights: Optional[PriorityWeights] = None,
    ) -> PriorityScheduleResponse:
        """Computes multi-factor task prioritization and recommendations."""
        project, tasks, dependencies = await cls.get_project_tasks_and_dependencies(project_id, db)

        if not tasks:
            return PriorityScheduleResponse(
                project_id=project_id,
                recommended_tasks=[],
                blocked_tasks=[],
                completed_tasks=[],
                weights=vars(weights or PriorityWeights()),
            )

        # Build prerequisites mapping
        prereqs: Dict[UUID, Set[UUID]] = {t.id: set() for t in tasks}
        for d in dependencies:
            if d.depends_on_task_id in prereqs:
                prereqs[d.task_id].add(d.depends_on_task_id)

        # Run CPM to identify critical path tasks
        critical_task_ids: Set[UUID] = set()
        cpm_inputs = [
            CpmTaskInput(
                id=t.id,
                duration=float(t.estimated_duration_hours),
                prerequisites=prereqs[t.id],
                title=t.title,
            )
            for t in tasks
        ]

        try:
            cpm_result = calculate_cpm(cpm_inputs)
            critical_task_ids = set(cpm_result.critical_tasks)
        except CycleDetectedError as exc:
            raise HTTPException(
                status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
                detail=str(exc),
            )
        except Exception:
            # If duration is missing on some task, proceed without critical path flag
            critical_task_ids = set()

        priority_inputs = [
            PriorityTaskInput(
                id=t.id,
                title=t.title,
                status=t.status,
                priority=t.priority,
                due_date=t.due_date,
                estimated_duration_hours=float(t.estimated_duration_hours) if t.estimated_duration_hours is not None else None,
                prerequisites=prereqs[t.id],
                is_critical=(t.id in critical_task_ids),
            )
            for t in tasks
        ]

        active_weights = weights or PriorityWeights()
        try:
            sched_result = compute_priority_schedule(
                tasks=priority_inputs,
                reference_date=reference_date or date.today(),
                weights=active_weights,
            )
        except (CycleDetectedError, InvalidDependencyError) as exc:
            raise HTTPException(
                status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
                detail=str(exc),
            )

        def map_ranked(items) -> List[PriorityTaskOutputSchema]:
            return [
                PriorityTaskOutputSchema(
                    id=item.id,
                    title=item.title,
                    priority=item.priority,
                    status=item.status,
                    due_date=item.due_date,
                    estimated_duration_hours=item.estimated_duration_hours,
                    is_eligible=item.is_eligible,
                    blocking_prerequisites=item.blocking_prerequisites,
                    is_critical=item.is_critical,
                    downstream_dependents_count=item.downstream_dependents_count,
                    total_score=item.total_score,
                    score_breakdown=ScoreBreakdownSchema(
                        priority_norm=item.score_breakdown.priority_norm,
                        urgency_norm=item.score_breakdown.urgency_norm,
                        critical_norm=item.score_breakdown.critical_norm,
                        downstream_norm=item.score_breakdown.downstream_norm,
                        effort_norm=item.score_breakdown.effort_norm,
                        weighted_total=item.score_breakdown.weighted_total,
                    ),
                    recommendation_reason=item.recommendation_reason,
                )
                for item in items
            ]

        return PriorityScheduleResponse(
            project_id=project_id,
            recommended_tasks=map_ranked(sched_result.recommended_tasks),
            blocked_tasks=map_ranked(sched_result.blocked_tasks),
            completed_tasks=map_ranked(sched_result.completed_tasks),
            weights=vars(active_weights),
        )

    @classmethod
    async def analyze_project_pert(
        cls,
        project_id: UUID,
        request: PertCalculationRequest,
        db: AsyncSession,
    ) -> PertAnalysisResponse:
        """Executes PERT three-point analysis with CPM critical-path variance integration."""
        project, tasks, dependencies = await cls.get_project_tasks_and_dependencies(project_id, db)

        task_lookup = {t.id: t for t in tasks}
        pert_estimates: List[PertTaskEstimate] = []

        # Validate that all estimated tasks belong to the project
        for est in request.estimates:
            if est.task_id not in task_lookup:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Task with ID '{est.task_id}' does not belong to project '{project_id}'.",
                )
            try:
                pert_est = PertTaskEstimate(
                    id=est.task_id,
                    optimistic=est.optimistic_hours,
                    most_likely=est.most_likely_hours,
                    pessimistic=est.pessimistic_hours,
                )
                pert_estimates.append(pert_est)
            except InvalidPertEstimateError as exc:
                raise HTTPException(
                    status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
                    detail=str(exc),
                )

        estimates_by_id = {pe.id: pe for pe in pert_estimates}

        # Build prerequisites mapping
        prereqs: Dict[UUID, Set[UUID]] = {t.id: set() for t in tasks}
        for d in dependencies:
            if d.depends_on_task_id in prereqs:
                prereqs[d.task_id].add(d.depends_on_task_id)

        # Run CPM using PERT expected durations for accurate critical path detection
        cpm_inputs = [
            CpmTaskInput(
                id=t.id,
                duration=estimates_by_id[t.id].expected_duration
                if t.id in estimates_by_id
                else float(t.estimated_duration_hours),
                prerequisites=prereqs[t.id],
                title=t.title,
            )
            for t in tasks
        ]

        critical_path_ids: List[UUID] = []
        try:
            cpm_res = calculate_cpm(cpm_inputs)
            critical_path_ids = cpm_res.critical_tasks
        except CycleDetectedError as exc:
            raise HTTPException(
                status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
                detail=str(exc),
            )
        except Exception:
            # Fallback to provided task list if CPM encounters issues
            critical_path_ids = [pe.id for pe in pert_estimates]

        pert_result = analyze_pert(
            task_estimates=pert_estimates,
            critical_path_task_ids=critical_path_ids,
            target_deadline_hours=request.target_deadline_hours,
        )

        task_metrics: Dict[str, PertTaskMetric] = {}
        for tid, est in pert_result.tasks.items():
            task_metrics[str(tid)] = PertTaskMetric(
                task_id=tid,
                optimistic_hours=est.optimistic,
                most_likely_hours=est.most_likely,
                pessimistic_hours=est.pessimistic,
                expected_duration_hours=est.expected_duration,
                variance=est.variance,
                standard_deviation=est.standard_deviation,
            )

        return PertAnalysisResponse(
            project_id=project_id,
            critical_path_expected_duration_hours=pert_result.critical_path_expected_duration,
            critical_path_variance=pert_result.critical_path_variance,
            critical_path_std_dev=pert_result.critical_path_std_dev,
            target_deadline_hours=pert_result.target_deadline,
            z_score=pert_result.z_score,
            probability_of_meeting_deadline=pert_result.probability_of_meeting_deadline,
            confidence_percentage=pert_result.confidence_percentage,
            tasks=task_metrics,
            assumptions=pert_result.assumptions,
        )
