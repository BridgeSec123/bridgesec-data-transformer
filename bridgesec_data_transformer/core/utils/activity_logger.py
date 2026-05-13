"""
Activity logging service.

Writes to the Supabase `activity_logs` table.
All exceptions are swallowed — logging must never break the main request flow.
"""
import logging

logger = logging.getLogger(__name__)


class ActivityLogger:
    """Static helper for writing tenant-scoped activity log entries."""

    @staticmethod
    def log(
        tenant_id=None,
        user_email=None,
        action=None,
        entity_name=None,
        db_name=None,
        details=None,
        status="success",
        ip_address=None,
    ) -> None:
        """
        Write a single activity log entry to Supabase.

        Args:
            tenant_id:   UUID string of the tenant (None for system tasks)
            user_email:  email of the acting user (None for system tasks)
            action:      one of login | logout | bulk_fetch | restore | create | delete | view
            entity_name: Okta entity type (e.g. "users", "policy_mfa")
            db_name:     snapshot DB name that was touched
            details:     arbitrary dict with extra context (counts, IDs, errors…)
            status:      success | error | partial_success
            ip_address:  client IP (optional)
        """
        try:
            from core.utils.supabase_activity_log import SupabaseActivityLog
            SupabaseActivityLog.log(
                user_email=user_email or "system",
                action=action or "unknown",
                tenant_id=str(tenant_id) if tenant_id else None,
                entity_name=entity_name,
                db_name=db_name,
                status=status,
                ip_address=ip_address,
                details=details or {},
            )
        except Exception as e:
            logger.warning(f"ActivityLogger.log failed (action={action}): {e}")
