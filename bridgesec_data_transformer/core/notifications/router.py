"""
Notification router — the single entry point for all notifications.

HOW IT WORKS:
  1. Reads notification_channels config from Supabase for the tenant.
  2. Filters channels by: is_enabled=True AND event_filter allows this event.
  3. Dashboard → writes directly to Supabase (synchronous, instant, no Celery).
  4. Slack / Teams / Email → queues a Celery task on the `notifications` queue
     (handled by a dedicated worker, never blocked by bulk fetch).

CALL SITE (one line anywhere in the app):
  from core.notifications import notify
  notify("bulk_fetch_failed", {"db_name": db_name, "error": str(e)}, tenant_id)
"""
import logging

from core.notifications.events import default_severity, INFO

logger = logging.getLogger(__name__)

# Channels that are dispatched synchronously (no Celery)
_SYNC_CHANNELS = {"dashboard"}

# Human-readable titles per event type.
# Falls back to a formatted version of the event_type string if not listed.
_TITLES: dict[str, str] = {
    "bulk_fetch_completed":               "Bulk fetch completed",
    "bulk_fetch_failed":                  "Bulk fetch failed",
    "bulk_fetch_partial":                 "Bulk fetch partially completed",
    "bulk_fetch_task_revoked":            "Bulk fetch cancelled",
    "anomaly_detected":                   "Anomaly detected — records missing",
    "diff_task_failed":                   "Change detection failed",
    "restore_completed":                  "Restore completed",
    "restore_failed":                     "Restore failed",
    "create_completed":                   "Create completed",
    "deletion_confirmed":                 "Deletion confirmed",
    "deletion_failed":                    "Deletion failed",
    "deletion_plan_expired":              "Deletion plan expired",
    "cross_tenant_migration_completed":   "Cross-tenant migration completed",
    "cross_tenant_migration_failed":      "Cross-tenant migration failed",
    "policy_created":                     "Policy created",
    "policy_updated":                     "Policy updated",
    "policy_deleted":                     "Policy deleted",
    "user_created":                       "User added",
    "user_removed":                       "User removed",
    "user_role_escalated":                "User role escalated",
    "user_login":                         "User login",
    "tenant_created":                     "Tenant created",
    "tenant_updated":                     "Tenant updated",
    "scheduled_fetch_skipped":            "Scheduled fetch skipped",
    "entity_config_changed":              "Entity config changed",
    "action_blocked":                     "Action blocked",
}


def _build_body(event_type: str, payload: dict) -> str:
    """Build a human-readable body string from the payload dict."""
    if not payload:
        return ""
    lines = []
    for key, val in payload.items():
        if val is not None:
            label = key.replace("_", " ").capitalize()
            lines.append(f"{label}: {val}")
    return "\n".join(lines)


def _channel_accepts(channel, event_type: str) -> bool:
    """
    Return True if the channel should receive this event.
    event_filter=None means all events are accepted.
    event_filter=[...] means only listed event types are accepted.
    """
    if channel.event_filter is None:
        return True
    return event_type in channel.event_filter


def notify(
    event_type: str,
    payload: dict,
    tenant_id: str,
    severity: str | None = None,
    user_id: str | None = None,
    title: str | None = None,
    body: str | None = None,
):
    """
    Emit a notification for an event.

    Args:
        event_type:  One of the constants in events.py (e.g. events.BULK_FETCH_FAILED)
        payload:     Arbitrary dict with context (db_name, entity_name, error, counts…)
        tenant_id:   UUID of the tenant — notifications are always tenant-scoped
        severity:    Override default severity. If None, resolved from events.EVENT_SEVERITY
        user_id:     Target a specific user. None = broadcast to all tenant users
        title:       Override auto-generated title
        body:        Override auto-generated body
    """
    if not tenant_id:
        logger.warning(f"notify() called for event '{event_type}' with no tenant_id — skipped")
        return

    resolved_severity = severity or default_severity(event_type)
    resolved_title    = title or _TITLES.get(event_type, event_type.replace("_", " ").capitalize())
    resolved_body     = body or _build_body(event_type, payload)
    metadata          = payload or {}

    # ── Dashboard is the in-app inbox — ALWAYS write it on every event. ───────
    # Unlike email/slack/teams it is not opt-in: the notifications table must
    # record every event so the in-app badge is always accurate, regardless of
    # which (or whether any) external channels are configured for the tenant.
    # ponytail: unconditional dashboard write; if per-tenant dashboard mute is
    # ever needed, gate this on an explicit notification_channels row.
    _write_dashboard(event_type, resolved_severity, resolved_title,
                     resolved_body, tenant_id, user_id, metadata)

    # ── External channels (email/slack/teams) are config-driven and optional ──
    try:
        from core.utils.supabase_notifications import SupabaseNotificationChannel
        channels = SupabaseNotificationChannel.get_enabled_for_tenant(str(tenant_id))
    except Exception as e:
        logger.error(f"notify() could not load channel config for tenant {tenant_id}: {e}")
        return  # dashboard already written above — external channels skipped

    # Resolve human-readable tenant label (okta_domain) once for all external channels.
    try:
        from core.utils.supabase_tenant import SupabaseTenant
        _t = SupabaseTenant.get_by_id(str(tenant_id))
        tenant_label = (_t.okta_domain if _t and _t.okta_domain else str(tenant_id))
    except Exception:
        tenant_label = str(tenant_id)

    for channel in channels:
        if channel.channel_type == "dashboard":
            continue  # already written unconditionally above
        if not _channel_accepts(channel, event_type):
            continue

        # Async — queued to `notifications` Celery queue.
        # Never blocks the caller, never competes with bulk fetch workers.
        _dispatch_async(
            channel_type=channel.channel_type,
            channel_config=channel.config or {},
            event_type=event_type,
            severity=resolved_severity,
            title=resolved_title,
            body=resolved_body,
            tenant_id=str(tenant_id),
            tenant_label=tenant_label,
            user_id=str(user_id) if user_id else None,
            metadata=metadata,
        )


def _write_dashboard(event_type, severity, title, body, tenant_id, user_id, metadata):
    """Write notification directly to Supabase. Called synchronously."""
    from core.notifications.channels.dashboard import DashboardChannel
    DashboardChannel().send(
        event_type=event_type,
        severity=severity,
        title=title,
        body=body,
        tenant_id=str(tenant_id),
        user_id=str(user_id) if user_id else None,
        metadata=metadata,
        channel_config={},
    )


def _dispatch_async(channel_type, channel_config, **kwargs):
    """Queue an external channel delivery task to the notifications Celery queue."""
    try:
        from core.notifications.tasks import dispatch_channel_notification
        dispatch_channel_notification.delay(
            channel_type=channel_type,
            channel_config=channel_config,
            **kwargs,
        )
        logger.debug(f"Queued {channel_type} notification for event '{kwargs.get('event_type')}'")
    except Exception as e:
        # Celery broker down — log and move on. Dashboard already written.
        logger.error(f"Failed to queue {channel_type} notification: {e}")
