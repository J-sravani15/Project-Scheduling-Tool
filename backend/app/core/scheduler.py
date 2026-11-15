import asyncio
import logging
from typing import Optional
from app.core.database import AsyncSessionLocal
from app.services.notification_service import NotificationService

logger = logging.getLogger("app.scheduler")

_checker_task: Optional[asyncio.Task] = None
_is_running: bool = False


async def run_deadline_checker_loop(interval_seconds: int = 60) -> None:
    """
    Background worker loop that periodically evaluates tasks approaching deadlines
    and overdue deliverables.
    Runs silently in the background and logs summary activity.
    """
    global _is_running
    logger.info(f"Deadline and academic alert background scheduler started (check interval: {interval_seconds}s).")
    _is_running = True

    try:
        while True:
            try:
                async with AsyncSessionLocal() as session:
                    d_stats = await NotificationService.check_and_generate_deadline_reminders(db=session)
                    a_stats = await NotificationService.check_and_generate_academic_alerts(db=session)

                    total_generated = (
                        d_stats["due_in_24h_generated"]
                        + d_stats["due_in_1h_generated"]
                        + d_stats["overdue_alerts_generated"]
                        + a_stats["milestone_alerts_generated"]
                        + a_stats["review_alerts_generated"]
                    )
                    if total_generated > 0:
                        logger.info(f"Generated {total_generated} notifications: deadlines={d_stats}, academic={a_stats}")

            except asyncio.CancelledError:
                logger.info("Deadline checker loop cancelled.")
                raise
            except Exception as e:
                logger.error(f"Error in deadline checker loop: {e}", exc_info=True)

            await asyncio.sleep(interval_seconds)

    finally:
        _is_running = False
        logger.info("Deadline checker loop stopped.")


def start_scheduler(interval_seconds: int = 60) -> Optional[asyncio.Task]:
    """
    Starts the deadline checker background task if not already running.
    Safe against multiple invocations and development reload.
    """
    global _checker_task
    if _checker_task is not None and not _checker_task.done():
        logger.warning("Scheduler task is already running; skipping duplicate start.")
        return _checker_task

    _checker_task = asyncio.create_task(run_deadline_checker_loop(interval_seconds=interval_seconds))
    return _checker_task


async def stop_scheduler() -> None:
    """
    Gracefully stops the deadline checker background task on application shutdown.
    """
    global _checker_task
    if _checker_task is not None and not _checker_task.done():
        logger.info("Stopping deadline checker background task...")
        _checker_task.cancel()
        try:
            await _checker_task
        except asyncio.CancelledError:
            pass
        _checker_task = None
