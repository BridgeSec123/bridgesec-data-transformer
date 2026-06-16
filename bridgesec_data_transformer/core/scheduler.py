import logging
from django.conf import settings
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


def _trigger_for_tenant(tenant_id: str):
    """Dispatch the scheduled bulk task for a specific tenant."""
    from core.tasks.bulk_tasks import run_scheduled_bulk_task_for_tenant
    run_scheduled_bulk_task_for_tenant.delay(tenant_id)


def start_scheduler():
    """
    Start APScheduler as a fallback trigger (opt-in via USE_APSCHEDULER=true).

    Reads all active tenants from Supabase at startup and registers one
    timezone-aware cron job per tenant. APScheduler handles timezone conversion
    natively — no UTC conversion needed here.

    In production, Celery Beat (celery.py beat_init signal) is the preferred
    scheduler. Use APScheduler INSTEAD of Beat, never alongside it — running
    both would double-dispatch each tenant per tick.

    Restart APScheduler to pick up tenant schedule changes from Supabase.
    """
    try:
        from core.utils.supabase_tenant import SupabaseTenant
        tenants, _ = SupabaseTenant.list_all(active_only=True, page=1, page_size=1000)
    except Exception as e:
        logger.error(
            f"APScheduler: could not load tenants from Supabase: {e}. Scheduler not started.",
            extra={'component': 'apscheduler'}
        )
        return

    if not tenants:
        logger.warning(
            "APScheduler: no active tenants found in Supabase. Scheduler not started.",
            extra={'component': 'apscheduler'}
        )
        return

    scheduler = BackgroundScheduler()
    registered = 0

    for tenant in tenants:
        if not tenant.scheduler_enabled:
            logger.info(
                f"APScheduler: tenant '{tenant.name}' has scheduler_enabled=False — skipping.",
                extra={'component': 'apscheduler', 'tenant_id': str(tenant.id)}
            )
            continue

        hour    = int(tenant.scheduler_hour or 0)
        minute  = int(tenant.scheduler_minute or 0)
        tz_name = tenant.scheduler_timezone or "UTC"

        try:
            from zoneinfo import ZoneInfo
            tz = ZoneInfo(tz_name)
        except Exception:
            logger.warning(
                f"APScheduler: unknown timezone '{tz_name}' for tenant '{tenant.name}', falling back to UTC.",
                extra={'component': 'apscheduler', 'tenant_id': str(tenant.id)}
            )
            from zoneinfo import ZoneInfo
            tz = ZoneInfo("UTC")

        scheduler.add_job(
            _trigger_for_tenant,
            trigger=CronTrigger(hour=hour, minute=minute, timezone=tz),
            id=f"bulk-fetch-{tenant.id}",
            name=f"Scheduled bulk fetch — {tenant.name}",
            args=[str(tenant.id)],
            replace_existing=True,
            max_instances=1,
        )
        registered += 1
        logger.info(
            f"APScheduler: registered '{tenant.name}' at {hour:02d}:{minute:02d} {tz_name}",
            extra={'component': 'apscheduler', 'tenant_id': str(tenant.id)}
        )

    if registered == 0:
        logger.warning(
            "APScheduler: all active tenants have scheduler_enabled=False. Scheduler not started.",
            extra={'component': 'apscheduler'}
        )
        return

    scheduler.start()
    logger.info(
        f"APScheduler started with {registered} per-tenant job(s).",
        extra={'component': 'apscheduler'}
    )
