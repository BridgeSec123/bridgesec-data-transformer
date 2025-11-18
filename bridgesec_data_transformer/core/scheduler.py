import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from core.tasks.bulk_tasks import run_bulk_entity_task

logger = logging.getLogger(__name__)


def trigger_bulk_task():
    """Wrapper function to trigger the Celery task without arguments."""
    run_bulk_entity_task.delay()


def start_scheduler():
    """
    Start the APScheduler to run bulk entity task daily at 1 AM.
    Uses in-memory job store (no database needed).
    """
    scheduler = BackgroundScheduler()

    # Schedule the bulk entity task to run every day at 12:00 AM UTC
    scheduler.add_job(
        trigger_bulk_task,  # Trigger Celery task via wrapper
        trigger=CronTrigger(hour=0, minute=0, timezone='UTC'),  # Daily at 12:00 AM UTC
        id="bulk_entity_task",
        name="Run bulk entity data fetch task",
        replace_existing=True,
        max_instances=1,  # Prevent overlapping runs
    )

    logger.info("APScheduler started. Bulk entity task scheduled to run daily at 12:00 AM UTC.")
    scheduler.start()
