"""
Celery task for async notification delivery to external channels.

WHY A SEPARATE TASK:
  Slack/Teams/Email involve outbound HTTP calls that can be slow or fail.
  Putting them in a Celery task means:
    1. The caller (bulk_tasks, views) is never blocked waiting for a webhook.
    2. Failed deliveries are retried automatically (max 3 times, 60s apart).
    3. This task is routed to the `notifications` queue which has its own
       dedicated worker — so a running bulk fetch (which saturates the
       `default` queue) never delays a critical Slack alert.
"""
import logging

from celery import shared_task

logger = logging.getLogger(__name__)

# Channel type → driver class (imported lazily to avoid circular imports at module load)
_CHANNEL_DRIVERS = {
    "slack":  "core.notifications.channels.slack.SlackChannel",
    "teams":  "core.notifications.channels.teams.TeamsChannel",
    "email":  "core.notifications.channels.email.EmailChannel",
}


def _load_driver(channel_type: str):
    """Import and instantiate a channel driver by dotted path."""
    dotted = _CHANNEL_DRIVERS.get(channel_type)
    if not dotted:
        raise ValueError(f"Unknown channel type: {channel_type}")
    module_path, class_name = dotted.rsplit(".", 1)
    import importlib
    module = importlib.import_module(module_path)
    return getattr(module, class_name)()


@shared_task(
    bind=True,
    queue="notifications",        # ← always goes to notifications queue, never default
    max_retries=3,
    default_retry_delay=60,       # 60s between retries
    name="core.notifications.tasks.dispatch_channel_notification",
)
def dispatch_channel_notification(
    self,
    channel_type: str,
    event_type: str,
    severity: str,
    title: str,
    body: str,
    tenant_id: str,
    tenant_label: str,
    user_id: str | None,
    metadata: dict,
    channel_config: dict,
):
    """
    Deliver a notification to a single external channel (slack / teams / email).

    Called by router.py once per enabled external channel.
    Dashboard is NOT handled here — it writes synchronously in router.py.
    """
    try:
        driver = _load_driver(channel_type)
        driver.send(
            event_type=event_type,
            severity=severity,
            title=title,
            body=body,
            tenant_id=tenant_id,
            tenant_label=tenant_label,
            user_id=user_id,
            metadata=metadata,
            channel_config=channel_config,
        )
    except Exception as exc:
        logger.warning(
            f"dispatch_channel_notification failed for {channel_type}/{event_type} "
            f"tenant={tenant_id} — attempt {self.request.retries + 1}/3: {exc}"
        )
        raise self.retry(exc=exc)
