from datetime import datetime, date, time, timedelta, timezone
from typing import List, Optional, Tuple, Dict, Any
from uuid import UUID
from sqlalchemy import select, func, and_, or_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.notification import ProjectNotification
from app.models.task import Task, TaskAssignment
from app.models.project import AcademicProject, ProjectMember
from app.models.milestone import AcademicMilestone
from app.models.review import ProjectReview
from app.models.user import User
from app.models.enums import NotificationType, TaskStatus, MilestoneStatus, ReviewStatus, UserRole


class NotificationService:
    @staticmethod
    async def create_notification(
        db: AsyncSession,
        recipient_id: UUID,
        title: str,
        message: str,
        notification_type: NotificationType,
        project_id: Optional[UUID] = None,
        task_id: Optional[UUID] = None,
        link_url: Optional[str] = None,
        scheduled_at: Optional[datetime] = None,
        sent_at: Optional[datetime] = None,
    ) -> ProjectNotification:
        """Creates and stores a persistent in-app notification."""
        notif = ProjectNotification(
            recipient_id=recipient_id,
            project_id=project_id,
            task_id=task_id,
            link_url=link_url,
            notification_type=notification_type,
            title=title,
            message=message,
            scheduled_at=scheduled_at,
            sent_at=sent_at or datetime.now(timezone.utc),
        )
        db.add(notif)
        await db.commit()
        await db.refresh(notif)
        return notif

    @staticmethod
    async def notify_task_assignment(
        db: AsyncSession,
        task: Task,
        recipient_id: UUID,
        assigner: User,
    ) -> Optional[ProjectNotification]:
        """
        Creates an in-app notification when a task is assigned to a student.
        Prevents duplicate notification if an assignment notification for this task/user was already sent.
        """
        # Duplicate check: check if task assignment notification was already generated
        existing = await db.execute(
            select(ProjectNotification).where(
                ProjectNotification.recipient_id == recipient_id,
                ProjectNotification.task_id == task.id,
                ProjectNotification.notification_type == NotificationType.TASK_ASSIGNED,
            )
        )
        if existing.scalar_one_or_none():
            return None

        # Fetch project for title
        proj_query = await db.execute(select(AcademicProject).where(AcademicProject.id == task.project_id))
        project = proj_query.scalar_one_or_none()
        project_title = project.title if project else "Academic Project"

        title = f"Task Assigned: {task.title}"
        message = (
            f"You have been assigned to task '{task.title}' in project '{project_title}' "
            f"by {assigner.full_name}. Due Date: {task.due_date}."
        )
        link_url = f"/projects/{task.project_id}?taskId={task.id}"

        return await NotificationService.create_notification(
            db=db,
            recipient_id=recipient_id,
            project_id=task.project_id,
            task_id=task.id,
            link_url=link_url,
            notification_type=NotificationType.TASK_ASSIGNED,
            title=title,
            message=message,
        )

    @staticmethod
    def get_review_type_name(review_number: int, feedback: Optional[str] = None) -> str:
        """
        Determines the academic review type name: Review 1, Review 2, Viva, or Review N.
        """
        if feedback and "viva" in feedback.lower():
            return "Viva"
        if review_number == 1:
            return "Review 1"
        elif review_number == 2:
            return "Review 2"
        elif review_number == 3:
            return "Viva"
        return f"Review {review_number}"

    @staticmethod
    async def get_enrolled_student_ids(db: AsyncSession, project_id: UUID) -> List[UUID]:
        """
        Returns all student recipient IDs enrolled in the given academic project.
        Includes project owner (if student) and all project members (who are students).
        Excludes faculty supervisors and external accounts.
        """
        proj_q = await db.execute(
            select(AcademicProject)
            .options(
                selectinload(AcademicProject.owner),
                selectinload(AcademicProject.members).selectinload(ProjectMember.user),
            )
            .where(AcademicProject.id == project_id)
        )
        project = proj_q.scalar_one_or_none()
        if not project:
            return []

        recipient_ids = set()
        if project.owner and project.owner.role == UserRole.STUDENT:
            recipient_ids.add(project.owner_id)
        elif not project.owner and project.owner_id:
            recipient_ids.add(project.owner_id)

        for m in project.members:
            if m.user and m.user.role == UserRole.STUDENT:
                recipient_ids.add(m.user_id)
            elif not m.user and m.user_id != project.faculty_guide_id:
                recipient_ids.add(m.user_id)

        if project.faculty_guide_id:
            recipient_ids.discard(project.faculty_guide_id)

        return list(recipient_ids)

    @staticmethod
    async def notify_review_scheduled(
        db: AsyncSession,
        review: ProjectReview,
        project: AcademicProject,
        faculty: User,
    ) -> List[ProjectNotification]:
        """
        Creates in-app notifications for all enrolled students in the project
        when a faculty guide schedules a project review.
        Idempotent: prevents duplicate notifications if the schedule request is retried.
        """
        student_ids = await NotificationService.get_enrolled_student_ids(db, project.id)
        if not student_ids:
            return []

        review_type = NotificationService.get_review_type_name(review.review_number, review.feedback)
        time_str = review.scheduled_at.strftime("%Y-%m-%d %H:%M UTC") if review.scheduled_at else "TBD"
        title = f"Review Scheduled: {review_type} - {project.title}"
        message = (
            f"Faculty guide {faculty.full_name} has scheduled {review_type} for project '{project.title}' "
            f"on {time_str}."
        )
        link_url = f"/projects/{project.id}"

        created_notifs = []
        for s_id in student_ids:
            # Duplicate check
            existing = await db.execute(
                select(ProjectNotification).where(
                    ProjectNotification.recipient_id == s_id,
                    ProjectNotification.project_id == project.id,
                    ProjectNotification.notification_type == NotificationType.REVIEW_REMINDER,
                    ProjectNotification.scheduled_at == review.scheduled_at,
                    ProjectNotification.title.ilike(f"%Scheduled%{review_type}%"),
                )
            )
            if existing.scalar_one_or_none():
                continue

            notif = await NotificationService.create_notification(
                db=db,
                recipient_id=s_id,
                project_id=project.id,
                link_url=link_url,
                notification_type=NotificationType.REVIEW_REMINDER,
                title=title,
                message=message,
                scheduled_at=review.scheduled_at,
            )
            created_notifs.append(notif)

        return created_notifs

    @staticmethod
    async def notify_review_rescheduled(
        db: AsyncSession,
        review: ProjectReview,
        project: AcademicProject,
        faculty: User,
        previous_scheduled_at: Optional[datetime] = None,
    ) -> List[ProjectNotification]:
        """
        Creates in-app notifications for all enrolled students in the project
        when a faculty guide reschedules a project review.
        """
        student_ids = await NotificationService.get_enrolled_student_ids(db, project.id)
        if not student_ids:
            return []

        review_type = NotificationService.get_review_type_name(review.review_number, review.feedback)
        new_time_str = review.scheduled_at.strftime("%Y-%m-%d %H:%M UTC") if review.scheduled_at else "TBD"
        title = f"Review Rescheduled: {review_type} - {project.title}"
        message = (
            f"Faculty guide {faculty.full_name} has rescheduled {review_type} for project '{project.title}' "
            f"to {new_time_str}."
        )
        link_url = f"/projects/{project.id}"

        created_notifs = []
        for s_id in student_ids:
            # Duplicate check
            existing = await db.execute(
                select(ProjectNotification).where(
                    ProjectNotification.recipient_id == s_id,
                    ProjectNotification.project_id == project.id,
                    ProjectNotification.notification_type == NotificationType.REVIEW_REMINDER,
                    ProjectNotification.scheduled_at == review.scheduled_at,
                    ProjectNotification.title.ilike(f"%Rescheduled%{review_type}%"),
                )
            )
            if existing.scalar_one_or_none():
                continue

            notif = await NotificationService.create_notification(
                db=db,
                recipient_id=s_id,
                project_id=project.id,
                link_url=link_url,
                notification_type=NotificationType.REVIEW_REMINDER,
                title=title,
                message=message,
                scheduled_at=review.scheduled_at,
            )
            created_notifs.append(notif)

        return created_notifs

    @staticmethod
    async def notify_review_cancelled(
        db: AsyncSession,
        review: ProjectReview,
        project: AcademicProject,
        faculty: User,
    ) -> List[ProjectNotification]:
        """
        Creates in-app notifications for all enrolled students in the project
        when a scheduled review is cancelled.
        """
        student_ids = await NotificationService.get_enrolled_student_ids(db, project.id)
        if not student_ids:
            return []

        review_type = NotificationService.get_review_type_name(review.review_number, review.feedback)
        time_str = review.scheduled_at.strftime("%Y-%m-%d %H:%M UTC") if review.scheduled_at else "TBD"
        title = f"Review Cancelled: {review_type} - {project.title}"
        message = (
            f"Faculty guide {faculty.full_name} has cancelled {review_type} for project '{project.title}' "
            f"originally scheduled for {time_str}."
        )
        link_url = f"/projects/{project.id}"

        created_notifs = []
        for s_id in student_ids:
            # Duplicate check
            existing = await db.execute(
                select(ProjectNotification).where(
                    ProjectNotification.recipient_id == s_id,
                    ProjectNotification.project_id == project.id,
                    ProjectNotification.notification_type == NotificationType.REVIEW_REMINDER,
                    ProjectNotification.title.ilike(f"%Cancelled%{review_type}%"),
                )
            )
            if existing.scalar_one_or_none():
                continue

            notif = await NotificationService.create_notification(
                db=db,
                recipient_id=s_id,
                project_id=project.id,
                link_url=link_url,
                notification_type=NotificationType.REVIEW_REMINDER,
                title=title,
                message=message,
                scheduled_at=review.scheduled_at,
            )
            created_notifs.append(notif)

        return created_notifs

    @staticmethod
    async def check_and_generate_deadline_reminders(
        db: AsyncSession,
        reference_now: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Scans all incomplete tasks and generates:
        1. 24-hour upcoming deadline reminders
        2. 1-hour upcoming deadline reminders
        3. Overdue task alerts (with single-instance prevention)
        Excludes completed tasks and avoids duplicate notifications.
        """
        now = reference_now or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        # Query all incomplete tasks
        query = (
            select(Task)
            .options(
                selectinload(Task.assignments),
                selectinload(Task.project),
            )
            .where(
                Task.status.in_([
                    TaskStatus.TODO,
                    TaskStatus.IN_PROGRESS,
                    TaskStatus.BLOCKED,
                ])
            )
        )
        result = await db.execute(query)
        tasks = list(result.scalars().all())

        stats = {
            "tasks_evaluated": len(tasks),
            "due_in_24h_generated": 0,
            "due_in_1h_generated": 0,
            "overdue_alerts_generated": 0,
        }

        for task in tasks:
            # Calculate exact end-of-day deadline in UTC
            deadline_dt = datetime.combine(task.due_date, time(23, 59, 59, tzinfo=timezone.utc))

            # Determine recipients
            if task.assignments:
                recipient_ids = [a.user_id for a in task.assignments]
            elif task.project:
                recipient_ids = [task.project.owner_id]
            else:
                continue

            link_url = f"/projects/{task.project_id}?taskId={task.id}"
            project_title = task.project.title if task.project else "Academic Project"

            # Case A: Task is Overdue
            if now > deadline_dt:
                for recipient_id in recipient_ids:
                    # Check if overdue alert was already created
                    existing = await db.execute(
                        select(ProjectNotification).where(
                            ProjectNotification.recipient_id == recipient_id,
                            ProjectNotification.task_id == task.id,
                            ProjectNotification.notification_type == NotificationType.OVERDUE_TASK,
                        )
                    )
                    if not existing.scalar_one_or_none():
                        await NotificationService.create_notification(
                            db=db,
                            recipient_id=recipient_id,
                            project_id=task.project_id,
                            task_id=task.id,
                            link_url=link_url,
                            notification_type=NotificationType.OVERDUE_TASK,
                            title=f"OVERDUE: Task '{task.title}'",
                            message=(
                                f"Task '{task.title}' in project '{project_title}' was due on "
                                f"{task.due_date} and is now overdue. Status: {task.status.value.replace('_', ' ').title()}."
                            ),
                        )
                        stats["overdue_alerts_generated"] += 1

                # If project has an assigned faculty guide, alert guide once for overdue task
                if task.project and task.project.faculty_guide_id:
                    fg_id = task.project.faculty_guide_id
                    existing_fg = await db.execute(
                        select(ProjectNotification).where(
                            ProjectNotification.recipient_id == fg_id,
                            ProjectNotification.task_id == task.id,
                            ProjectNotification.notification_type == NotificationType.OVERDUE_TASK,
                        )
                    )
                    if not existing_fg.scalar_one_or_none():
                        await NotificationService.create_notification(
                            db=db,
                            recipient_id=fg_id,
                            project_id=task.project_id,
                            task_id=task.id,
                            link_url=link_url,
                            notification_type=NotificationType.OVERDUE_TASK,
                            title=f"Academic Alert: Overdue Task in '{project_title}'",
                            message=(
                                f"Task '{task.title}' in supervised project '{project_title}' is overdue "
                                f"(deadline: {task.due_date})."
                            ),
                        )
                        stats["overdue_alerts_generated"] += 1

            # Case B: Task is Approaching Deadline
            else:
                time_remaining = deadline_dt - now

                # 1-Hour Reminder
                if timedelta(0) < time_remaining <= timedelta(hours=1):
                    for recipient_id in recipient_ids:
                        existing = await db.execute(
                            select(ProjectNotification).where(
                                ProjectNotification.recipient_id == recipient_id,
                                ProjectNotification.task_id == task.id,
                                ProjectNotification.notification_type == NotificationType.DUE_DATE_REMINDER,
                                ProjectNotification.title.ilike("%1 Hour%"),
                            )
                        )
                        if not existing.scalar_one_or_none():
                            await NotificationService.create_notification(
                                db=db,
                                recipient_id=recipient_id,
                                project_id=task.project_id,
                                task_id=task.id,
                                link_url=link_url,
                                notification_type=NotificationType.DUE_DATE_REMINDER,
                                title=f"Urgent: Task '{task.title}' Due in 1 Hour",
                                message=(
                                    f"Task '{task.title}' in project '{project_title}' is due today at 23:59 UTC "
                                    f"({task.due_date}). Please submit your deliverables."
                                ),
                            )
                            stats["due_in_1h_generated"] += 1

                # 24-Hour Reminder
                elif timedelta(hours=1) < time_remaining <= timedelta(hours=24):
                    for recipient_id in recipient_ids:
                        existing = await db.execute(
                            select(ProjectNotification).where(
                                ProjectNotification.recipient_id == recipient_id,
                                ProjectNotification.task_id == task.id,
                                ProjectNotification.notification_type == NotificationType.DUE_DATE_REMINDER,
                                ProjectNotification.title.ilike("%24 Hours%"),
                            )
                        )
                        if not existing.scalar_one_or_none():
                            await NotificationService.create_notification(
                                db=db,
                                recipient_id=recipient_id,
                                project_id=task.project_id,
                                task_id=task.id,
                                link_url=link_url,
                                notification_type=NotificationType.DUE_DATE_REMINDER,
                                title=f"Reminder: Task '{task.title}' Due in 24 Hours",
                                message=(
                                    f"Task '{task.title}' in project '{project_title}' is due tomorrow "
                                    f"({task.due_date})."
                                ),
                            )
                            stats["due_in_24h_generated"] += 1

        return stats

    @staticmethod
    async def check_and_generate_academic_alerts(
        db: AsyncSession,
        reference_now: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Evaluates milestones and reviews to alert owners and faculty guides:
        - Upcoming milestones (within 3 days)
        - Approaching viva/reviews (within 2 days)
        """
        now = reference_now or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        stats = {
            "milestone_alerts_generated": 0,
            "review_alerts_generated": 0,
        }

        # 1. Milestones approaching planned_date within 3 days
        m_query = (
            select(AcademicMilestone)
            .options(selectinload(AcademicMilestone.project))
            .where(
                AcademicMilestone.status.in_([MilestoneStatus.PENDING, MilestoneStatus.IN_PROGRESS])
            )
        )
        milestones = list((await db.execute(m_query)).scalars().all())

        for ms in milestones:
            if not ms.planned_date or not ms.project:
                continue
            ms_deadline = datetime.combine(ms.planned_date, time(23, 59, 59, tzinfo=timezone.utc))
            time_left = ms_deadline - now

            if timedelta(0) <= time_left <= timedelta(days=3):
                # Alert project owner and faculty guide
                target_users = [ms.project.owner_id]
                if ms.project.faculty_guide_id:
                    target_users.append(ms.project.faculty_guide_id)

                for u_id in target_users:
                    existing = await db.execute(
                        select(ProjectNotification).where(
                            ProjectNotification.recipient_id == u_id,
                            ProjectNotification.project_id == ms.project_id,
                            ProjectNotification.notification_type == NotificationType.MILESTONE_REMINDER,
                            ProjectNotification.title.ilike(f"%{ms.title}%"),
                        )
                    )
                    if not existing.scalar_one_or_none():
                        await NotificationService.create_notification(
                            db=db,
                            recipient_id=u_id,
                            project_id=ms.project_id,
                            link_url=f"/projects/{ms.project_id}/milestones",
                            notification_type=NotificationType.MILESTONE_REMINDER,
                            title=f"Academic Milestone Approaching: {ms.title}",
                            message=(
                                f"Academic milestone '{ms.title}' in project '{ms.project.title}' is planned for "
                                f"{ms.planned_date}. Review readiness and verify deliverables."
                            ),
                        )
                        stats["milestone_alerts_generated"] += 1

        # 2. Reviews scheduled within 2 days
        r_query = (
            select(ProjectReview)
            .options(selectinload(ProjectReview.project))
            .where(ProjectReview.status == ReviewStatus.SCHEDULED)
        )
        reviews = list((await db.execute(r_query)).scalars().all())

        for rev in reviews:
            if not rev.scheduled_at or not rev.project:
                continue
            r_time = rev.scheduled_at
            if r_time.tzinfo is None:
                r_time = r_time.replace(tzinfo=timezone.utc)
            time_left = r_time - now

            if timedelta(0) <= time_left <= timedelta(days=2):
                enrolled_students = await NotificationService.get_enrolled_student_ids(db, rev.project_id)
                target_users = list(set(enrolled_students + ([rev.faculty_id] if rev.faculty_id else [])))
                for u_id in target_users:
                    existing = await db.execute(
                        select(ProjectNotification).where(
                            ProjectNotification.recipient_id == u_id,
                            ProjectNotification.project_id == rev.project_id,
                            ProjectNotification.notification_type == NotificationType.REVIEW_REMINDER,
                            ProjectNotification.title.ilike(f"%Review #{rev.review_number}%"),
                        )
                    )
                    if not existing.scalar_one_or_none():
                        await NotificationService.create_notification(
                            db=db,
                            recipient_id=u_id,
                            project_id=rev.project_id,
                            link_url=f"/projects/{rev.project_id}",
                            notification_type=NotificationType.REVIEW_REMINDER,
                            title=f"Upcoming Review #{rev.review_number}: {rev.project.title}",
                            message=(
                                f"Project Review #{rev.review_number} for '{rev.project.title}' is scheduled for "
                                f"{rev.scheduled_at.strftime('%Y-%m-%d %H:%M UTC')}."
                            ),
                        )
                        stats["review_alerts_generated"] += 1

        return stats

    @staticmethod
    async def get_user_notifications(
        db: AsyncSession,
        user_id: UUID,
        unread_only: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[ProjectNotification], int, int]:
        """
        Retrieves notifications specifically for user_id, ordered by newest first.
        Returns: (items, unread_count, total_count)
        """
        # Base condition
        conditions = [ProjectNotification.recipient_id == user_id]

        # Total count
        total_q = select(func.count()).select_from(ProjectNotification).where(*conditions)
        total_count = (await db.execute(total_q)).scalar() or 0

        # Unread count
        unread_q = select(func.count()).select_from(ProjectNotification).where(
            ProjectNotification.recipient_id == user_id,
            ProjectNotification.read_at.is_(None),
        )
        unread_count = (await db.execute(unread_q)).scalar() or 0

        # Filter if unread_only requested
        if unread_only:
            conditions.append(ProjectNotification.read_at.is_(None))

        query = (
            select(ProjectNotification)
            .where(*conditions)
            .order_by(ProjectNotification.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(query)
        items = list(result.scalars().all())

        return items, unread_count, total_count

    @staticmethod
    async def mark_as_read(
        db: AsyncSession,
        notification_id: UUID,
        user_id: UUID,
    ) -> Optional[ProjectNotification]:
        """Marks a notification as read if it belongs to user_id."""
        query = await db.execute(
            select(ProjectNotification).where(
                ProjectNotification.id == notification_id,
                ProjectNotification.recipient_id == user_id,
            )
        )
        notif = query.scalar_one_or_none()
        if not notif:
            return None

        if not notif.read_at:
            notif.read_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(notif)

        return notif

    @staticmethod
    async def mark_all_as_read(
        db: AsyncSession,
        user_id: UUID,
    ) -> int:
        """Marks all unread notifications for user_id as read."""
        now = datetime.now(timezone.utc)
        stmt = (
            update(ProjectNotification)
            .where(
                ProjectNotification.recipient_id == user_id,
                ProjectNotification.read_at.is_(None),
            )
            .values(read_at=now)
        )
        res = await db.execute(stmt)
        await db.commit()
        return res.rowcount
