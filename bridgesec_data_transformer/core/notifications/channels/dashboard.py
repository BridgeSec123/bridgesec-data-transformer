"""
Dashboard channel — writes directly to Supabase `notifications` table.

This is the only channel that is NOT dispatched via Celery.
It runs synchronously inside notify() so the in-app badge always
updates instantly, even when all Celery workers are busy bulk-fetching.
"""
import logging

from core.notifications.channels.base import BaseChannel

logger = logging.getLogger(__name__)


class DashboardChannel(BaseChannel):

    def send(self, event_type, severity, title, body, tenant_id,
             tenant_label=None, user_id=None, metadata=None, channel_config=None):  # tenant_label unused: dashboard scopes by tenant_id, not display label
        from core.utils.supabase_notifications import SupabaseNotification
        try:
            SupabaseNotification.create(
                tenant_id=tenant_id,
                event_type=event_type,
                severity=severity,
                title=title,
                body=body,
                metadata=metadata,
                user_id=user_id,
            )
            logger.debug(f"Dashboard notification written: [{severity}] {event_type} tenant={tenant_id}")
        except Exception as e:
            # Never let a failed dashboard write crash the caller.
            # The operation (bulk fetch, restore, etc.) already completed —
            # a missing notification badge is far less harmful than an unhandled exception.
            logger.error(f"DashboardChannel.send failed for {event_type} tenant={tenant_id}: {e}")
