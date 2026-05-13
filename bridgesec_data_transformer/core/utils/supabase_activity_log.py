"""
Supabase-backed Activity Log helper.

Replaces core/models/activity_log.py and activity_logger.py.
Writes to the `activity_logs` table (see supabase/migrations/001_rbac_schema.sql).
"""
import logging
from datetime import datetime

from core.utils.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

TABLE = "activity_logs"

VALID_ACTIONS = {"login", "logout", "bulk_fetch", "restore", "create", "delete", "view"}


class SupabaseActivityLog:
    """Static helpers for writing and querying activity logs."""

    @staticmethod
    def log(
        user_email: str,
        action: str,
        tenant_id: str = None,
        entity_name: str = None,
        db_name: str = None,
        status: str = "success",
        ip_address: str = None,
        details: dict = None,
    ) -> None:
        """
        Insert one activity log row. Swallows all exceptions so logging
        never breaks the request flow.
        """
        try:
            row = {
                "user_email":  user_email,
                "action":      action,
                "tenant_id":   str(tenant_id) if tenant_id else None,
                "entity_name": entity_name,
                "db_name":     db_name,
                "status":      status,
                "ip_address":  ip_address,
                "details":     details or {},
                "timestamp":   datetime.utcnow().isoformat(),
            }
            get_supabase_client().table(TABLE).insert(row).execute()
        except Exception as e:
            logger.warning(f"SupabaseActivityLog.log() failed (non-fatal): {e}")

    @staticmethod
    def list_for_tenant(
        tenant_id: str,
        action: str = None,
        user_email: str = None,
        date_from: str = None,
        date_to: str = None,
        page: int = 1,
        page_size: int = 20,
    ):
        """
        Return paginated (logs, total) for a specific tenant.
        Optional filters: action, user_email, date_from/date_to (ISO strings).
        """
        try:
            offset = (page - 1) * page_size
            query = (
                get_supabase_client()
                .table(TABLE)
                .select("*", count="exact")
                .eq("tenant_id", str(tenant_id))
                .order("timestamp", desc=True)
            )
            if action:
                query = query.eq("action", action)
            if user_email:
                query = query.eq("user_email", user_email)
            if date_from:
                query = query.gte("timestamp", date_from)
            if date_to:
                query = query.lte("timestamp", date_to)
            result = query.range(offset, offset + page_size - 1).execute()
            return result.data or [], result.count or 0
        except Exception as e:
            logger.error(f"SupabaseActivityLog.list_for_tenant() failed: {e}")
            return [], 0
