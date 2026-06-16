# bridgesec_data_transformer/celery_app.py
from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.signals import beat_init
import logging.config
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bridgesec_data_transformer.settings")

app = Celery("bridgesec_data_transformer")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
logging.config.dictConfig(settings.LOGGING)


# ── Beat startup: register per-tenant exact schedules ─────────────────────────
# beat_init fires ONLY when `celery beat` starts — not in web/worker processes.
# Reads all active tenants from Supabase once and registers one exact crontab
# per tenant. Changes to tenant schedules take effect after Beat is restarted.

@beat_init.connect
def on_beat_init(sender, **kwargs):
    _load_tenant_beat_schedules(sender.scheduler)


def _to_utc_hour_minute(hour: int, minute: int, tz_name: str):
    """Convert a local hour:minute in tz_name to UTC (hour, minute)."""
    import datetime
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(tz_name or "UTC")
        today = datetime.date.today()
        local_dt = datetime.datetime(today.year, today.month, today.day, hour, minute, tzinfo=tz)
        utc_dt = local_dt.astimezone(datetime.timezone.utc)
        return utc_dt.hour, utc_dt.minute
    except Exception:
        return hour, minute  # fallback: treat as UTC


def _load_tenant_beat_schedules(scheduler):
    """Read Supabase once at Beat startup and register one exact crontab per active tenant."""
    import logging
    from celery.schedules import crontab

    logger = logging.getLogger(__name__)

    try:
        from core.utils.supabase_tenant import SupabaseTenant
        tenants, _ = SupabaseTenant.list_all(active_only=True, page=1, page_size=1000)
    except Exception as e:
        logger.error(
            f"Beat schedule: could not load tenants from Supabase: {e}. "
            "No per-tenant tasks registered.",
            extra={'component': 'celery_beat'}
        )
        return

    if not tenants:
        logger.warning(
            "Beat schedule: no active tenants found in Supabase. "
            "No per-tenant tasks registered.",
            extra={'component': 'celery_beat'}
        )
        return

    # Remove stale per-tenant entries left by a previous Beat run in the shelve file.
    for key in list(scheduler.data.keys()):
        if key.startswith("bulk-fetch-"):
            del scheduler.data[key]

    entries = {}
    for tenant in tenants:
        if not tenant.scheduler_enabled:
            logger.info(
                f"Beat schedule: tenant '{tenant.name}' has scheduler_enabled=False — skipping.",
                extra={'component': 'celery_beat', 'tenant_id': str(tenant.id)}
            )
            continue

        hour    = int(tenant.scheduler_hour or 0)
        minute  = int(tenant.scheduler_minute or 0)
        tz_name = tenant.scheduler_timezone or "UTC"
        utc_h, utc_m = _to_utc_hour_minute(hour, minute, tz_name)

        entries[f"bulk-fetch-{tenant.id}"] = {
            "task":     "core.tasks.bulk_tasks.run_scheduled_bulk_task_for_tenant",
            "schedule": crontab(hour=utc_h, minute=utc_m),
            "kwargs":   {"tenant_id": str(tenant.id)},
        }
        logger.info(
            f"Beat schedule: registered '{tenant.name}' → "
            f"{tz_name} {hour:02d}:{minute:02d} (UTC {utc_h:02d}:{utc_m:02d})",
            extra={'component': 'celery_beat', 'tenant_id': str(tenant.id)}
        )

    if entries:
        scheduler.update_from_dict(entries)
        logger.info(
            f"Beat schedule: {len(entries)} per-tenant task(s) registered.",
            extra={'component': 'celery_beat'}
        )
    else:
        logger.warning(
            "Beat schedule: all active tenants have scheduler_enabled=False. "
            "No tasks registered.",
            extra={'component': 'celery_beat'}
        )
