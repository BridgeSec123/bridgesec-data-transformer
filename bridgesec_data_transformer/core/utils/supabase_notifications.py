"""
Supabase-backed helpers for the notification system.

Two tables:
  notification_channels — per-tenant config (which channels are enabled + webhook URLs)
  notifications         — in-app dashboard inbox (unread items per user/tenant)
"""
import logging

from core.utils.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

CHANNELS_TABLE = "notification_channels"
NOTIFICATIONS_TABLE = "notifications"

VALID_CHANNEL_TYPES = {"dashboard", "slack", "teams", "email"}
VALID_SEVERITIES = {"info", "warning", "error", "critical"}


# ─────────────────────────────────────────────────────────────
# NotificationChannel
# ─────────────────────────────────────────────────────────────

class SupabaseNotificationChannel:
    """Lightweight object backed by a notification_channels row."""

    def __init__(self, row: dict):
        self.id           = row.get("id")
        self.tenant_id    = row.get("tenant_id")
        self.channel_type = row.get("channel_type")
        self.is_enabled   = row.get("is_enabled", True)
        self.config       = row.get("config") or {}
        self.event_filter = row.get("event_filter")   # None = all events
        self.created_at   = row.get("created_at")
        self.updated_at   = row.get("updated_at")
        self._row         = row

    def to_dict(self) -> dict:
        return {
            "id":           self.id,
            "tenant_id":    str(self.tenant_id),
            "channel_type": self.channel_type,
            "is_enabled":   self.is_enabled,
            "config":       self.config,
            "event_filter": self.event_filter,
            "created_at":   self.created_at,
            "updated_at":   self.updated_at,
        }

    @classmethod
    def list_for_tenant(cls, tenant_id: str) -> list:
        """Return all channel configs for a tenant."""
        try:
            result = (
                get_supabase_client()
                .table(CHANNELS_TABLE)
                .select("*")
                .eq("tenant_id", str(tenant_id))
                .order("channel_type")
                .execute()
            )
            return [cls(row) for row in (result.data or [])]
        except Exception as e:
            logger.error(f"SupabaseNotificationChannel.list_for_tenant({tenant_id}) failed: {e}")
            return []

    @classmethod
    def get_by_id(cls, channel_id: str, tenant_id: str):
        """Return channel by id scoped to tenant, or None."""
        try:
            result = (
                get_supabase_client()
                .table(CHANNELS_TABLE)
                .select("*")
                .eq("id", str(channel_id))
                .eq("tenant_id", str(tenant_id))
                .limit(1)
                .execute()
            )
            return cls(result.data[0]) if result.data else None
        except Exception as e:
            logger.error(f"SupabaseNotificationChannel.get_by_id({channel_id}) failed: {e}")
            return None

    @classmethod
    def get_enabled_for_tenant(cls, tenant_id: str) -> list:
        """Return only enabled channels for a tenant (used by router)."""
        try:
            result = (
                get_supabase_client()
                .table(CHANNELS_TABLE)
                .select("*")
                .eq("tenant_id", str(tenant_id))
                .eq("is_enabled", True)
                .execute()
            )
            return [cls(row) for row in (result.data or [])]
        except Exception as e:
            logger.error(f"SupabaseNotificationChannel.get_enabled_for_tenant({tenant_id}) failed: {e}")
            return []

    @classmethod
    def upsert(cls, tenant_id: str, channel_type: str, data: dict):
        """
        Create or update a channel config for (tenant_id, channel_type).
        Uses the UNIQUE constraint so re-saving is always safe.
        Returns the saved SupabaseNotificationChannel.
        """
        try:
            payload = {
                "tenant_id":    str(tenant_id),
                "channel_type": channel_type,
                **data,
            }
            result = (
                get_supabase_client()
                .table(CHANNELS_TABLE)
                .upsert(payload, on_conflict="tenant_id,channel_type")
                .execute()
            )
            if result.data:
                return cls(result.data[0])
            raise ValueError("Supabase upsert returned no data")
        except Exception as e:
            logger.error(f"SupabaseNotificationChannel.upsert({tenant_id}, {channel_type}) failed: {e}")
            raise

    @classmethod
    def update(cls, channel_id: str, tenant_id: str, data: dict):
        """Partial update on a channel row. Returns updated object or None."""
        try:
            result = (
                get_supabase_client()
                .table(CHANNELS_TABLE)
                .update(data)
                .eq("id", str(channel_id))
                .eq("tenant_id", str(tenant_id))
                .execute()
            )
            return cls(result.data[0]) if result.data else None
        except Exception as e:
            logger.error(f"SupabaseNotificationChannel.update({channel_id}) failed: {e}")
            raise

    @classmethod
    def delete(cls, channel_id: str, tenant_id: str) -> bool:
        """Delete a channel config. Returns True on success."""
        try:
            result = (
                get_supabase_client()
                .table(CHANNELS_TABLE)
                .delete()
                .eq("id", str(channel_id))
                .eq("tenant_id", str(tenant_id))
                .execute()
            )
            return bool(result.data)
        except Exception as e:
            logger.error(f"SupabaseNotificationChannel.delete({channel_id}) failed: {e}")
            return False


# ─────────────────────────────────────────────────────────────
# Notification (in-app inbox)
# ─────────────────────────────────────────────────────────────

class SupabaseNotification:
    """Lightweight object backed by a notifications row."""

    def __init__(self, row: dict):
        self.id         = row.get("id")
        self.tenant_id  = row.get("tenant_id")
        self.user_id    = row.get("user_id")       # None = broadcast
        self.event_type = row.get("event_type")
        self.severity   = row.get("severity", "info")
        self.title      = row.get("title", "")
        self.body       = row.get("body", "")
        self.metadata   = row.get("metadata") or {}
        self.is_read    = row.get("is_read", False)
        self.created_at = row.get("created_at")
        self._row       = row

    def to_dict(self) -> dict:
        return {
            "id":         self.id,
            "tenant_id":  str(self.tenant_id),
            "user_id":    str(self.user_id) if self.user_id else None,
            "event_type": self.event_type,
            "severity":   self.severity,
            "title":      self.title,
            "body":       self.body,
            "metadata":   self.metadata,
            "is_read":    self.is_read,
            "created_at": self.created_at,
        }

    @classmethod
    def create(cls, tenant_id: str, event_type: str, severity: str,
               title: str, body: str = "", metadata: dict = None, user_id: str = None):
        """Insert a new notification row. Returns the created object."""
        try:
            payload = {
                "tenant_id":  str(tenant_id),
                "event_type": event_type,
                "severity":   severity,
                "title":      title,
                "body":       body,
                "metadata":   metadata or {},
                "is_read":    False,
            }
            if user_id:
                payload["user_id"] = str(user_id)

            result = (
                get_supabase_client()
                .table(NOTIFICATIONS_TABLE)
                .insert(payload)
                .execute()
            )
            if result.data:
                return cls(result.data[0])
            raise ValueError("Supabase insert returned no data")
        except Exception as e:
            logger.error(f"SupabaseNotification.create({tenant_id}, {event_type}) failed: {e}")
            raise

    @classmethod
    def list_for_user(cls, tenant_id: str, user_id: str = None,
                      is_read: bool = None, severity: str = None,
                      event_type: str = None, page: int = 1, page_size: int = 20):
        """
        Return paginated (notifications, total) for a user.
        Includes both user-specific rows (user_id = user_id) and
        broadcast rows (user_id IS NULL) for the tenant.
        """
        try:
            offset = (page - 1) * page_size
            query = (
                get_supabase_client()
                .table(NOTIFICATIONS_TABLE)
                .select("*", count="exact")
                .eq("tenant_id", str(tenant_id))
            )

            # user sees their own + broadcast rows
            if user_id:
                query = query.or_(f"user_id.eq.{user_id},user_id.is.null")

            if is_read is not None:
                query = query.eq("is_read", is_read)
            if severity:
                query = query.eq("severity", severity)
            if event_type:
                query = query.eq("event_type", event_type)

            result = (
                query
                .order("created_at", desc=True)
                .range(offset, offset + page_size - 1)
                .execute()
            )
            return [cls(row) for row in (result.data or [])], (result.count or 0)
        except Exception as e:
            logger.error(f"SupabaseNotification.list_for_user({tenant_id}) failed: {e}")
            return [], 0

    @classmethod
    def unread_count(cls, tenant_id: str, user_id: str = None) -> int:
        """Return count of unread notifications for a user."""
        try:
            query = (
                get_supabase_client()
                .table(NOTIFICATIONS_TABLE)
                .select("id", count="exact")
                .eq("tenant_id", str(tenant_id))
                .eq("is_read", False)
            )
            if user_id:
                query = query.or_(f"user_id.eq.{user_id},user_id.is.null")
            result = query.execute()
            return result.count or 0
        except Exception as e:
            logger.error(f"SupabaseNotification.unread_count({tenant_id}) failed: {e}")
            return 0

    @classmethod
    def mark_read(cls, notification_id: str, tenant_id: str) -> bool:
        """Mark a single notification as read. Returns True on success."""
        try:
            result = (
                get_supabase_client()
                .table(NOTIFICATIONS_TABLE)
                .update({"is_read": True})
                .eq("id", str(notification_id))
                .eq("tenant_id", str(tenant_id))
                .execute()
            )
            return bool(result.data)
        except Exception as e:
            logger.error(f"SupabaseNotification.mark_read({notification_id}) failed: {e}")
            return False

    @classmethod
    def mark_all_read(cls, tenant_id: str, user_id: str = None) -> int:
        """Mark all unread notifications as read. Returns count updated."""
        try:
            query = (
                get_supabase_client()
                .table(NOTIFICATIONS_TABLE)
                .update({"is_read": True})
                .eq("tenant_id", str(tenant_id))
                .eq("is_read", False)
            )
            if user_id:
                query = query.or_(f"user_id.eq.{user_id},user_id.is.null")
            result = query.execute()
            return len(result.data) if result.data else 0
        except Exception as e:
            logger.error(f"SupabaseNotification.mark_all_read({tenant_id}) failed: {e}")
            return 0

    @classmethod
    def delete(cls, notification_id: str, tenant_id: str) -> bool:
        """Delete a notification. Returns True on success."""
        try:
            result = (
                get_supabase_client()
                .table(NOTIFICATIONS_TABLE)
                .delete()
                .eq("id", str(notification_id))
                .eq("tenant_id", str(tenant_id))
                .execute()
            )
            return bool(result.data)
        except Exception as e:
            logger.error(f"SupabaseNotification.delete({notification_id}) failed: {e}")
            return False
