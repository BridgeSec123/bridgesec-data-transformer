"""
Notification event type constants and their default severity.

Every call to notify() uses these constants — no raw strings in application code.
Adding a new event = add one entry here + one call site. Nothing else changes.
"""

# ── Severity levels ───────────────────────────────────────────────────────────
INFO     = "info"
WARNING  = "warning"
ERROR    = "error"
CRITICAL = "critical"

# ── Event types ───────────────────────────────────────────────────────────────

# Bulk fetch
BULK_FETCH_COMPLETED      = "bulk_fetch_completed"
BULK_FETCH_FAILED         = "bulk_fetch_failed"
BULK_FETCH_PARTIAL        = "bulk_fetch_partial"
BULK_FETCH_TASK_REVOKED   = "bulk_fetch_task_revoked"

# Diff / change detection
ANOMALY_DETECTED          = "anomaly_detected"
DIFF_TASK_FAILED          = "diff_task_failed"

# Restore / create / delete
RESTORE_COMPLETED         = "restore_completed"
RESTORE_FAILED            = "restore_failed"
CREATE_COMPLETED          = "create_completed"
DELETION_CONFIRMED        = "deletion_confirmed"
DELETION_FAILED           = "deletion_failed"
DELETION_PLAN_EXPIRED     = "deletion_plan_expired"

# Cross-tenant migration
CROSS_TENANT_MIGRATION_COMPLETED = "cross_tenant_migration_completed"
CROSS_TENANT_MIGRATION_FAILED    = "cross_tenant_migration_failed"

# Policy
POLICY_CREATED = "policy_created"
POLICY_UPDATED = "policy_updated"
POLICY_DELETED = "policy_deleted"

# User management
USER_CREATED        = "user_created"
USER_REMOVED        = "user_removed"
USER_ROLE_ESCALATED = "user_role_escalated"

# Auth
USER_LOGIN = "user_login"

# Tenant
TENANT_CREATED = "tenant_created"
TENANT_UPDATED = "tenant_updated"

# Scheduler
SCHEDULED_FETCH_SKIPPED = "scheduled_fetch_skipped"

# Entity config
ENTITY_CONFIG_CHANGED = "entity_config_changed"

# Action blocked (e.g. restore attempted during bulk fetch)
ACTION_BLOCKED = "action_blocked"


# ── Default severity per event ────────────────────────────────────────────────
# Router uses this when caller does not pass severity explicitly.

EVENT_SEVERITY: dict[str, str] = {
    # critical
    BULK_FETCH_FAILED:                CRITICAL,
    ANOMALY_DETECTED:                 CRITICAL,
    DELETION_CONFIRMED:               CRITICAL,
    CROSS_TENANT_MIGRATION_FAILED:    CRITICAL,
    POLICY_DELETED:                   CRITICAL,
    USER_ROLE_ESCALATED:              CRITICAL,

    # error
    BULK_FETCH_PARTIAL:               ERROR,
    RESTORE_FAILED:                   ERROR,
    DELETION_FAILED:                  ERROR,
    DIFF_TASK_FAILED:                 ERROR,

    # warning
    BULK_FETCH_TASK_REVOKED:          WARNING,
    DELETION_PLAN_EXPIRED:            WARNING,
    POLICY_UPDATED:                   WARNING,
    SCHEDULED_FETCH_SKIPPED:          WARNING,
    ACTION_BLOCKED:                   WARNING,

    # info
    BULK_FETCH_COMPLETED:             INFO,
    RESTORE_COMPLETED:                INFO,
    CREATE_COMPLETED:                 INFO,
    CROSS_TENANT_MIGRATION_COMPLETED: INFO,
    POLICY_CREATED:                   INFO,
    USER_CREATED:                     INFO,
    USER_REMOVED:                     INFO,
    USER_LOGIN:                       INFO,
    TENANT_CREATED:                   INFO,
    TENANT_UPDATED:                   INFO,
    ENTITY_CONFIG_CHANGED:            INFO,
}


def default_severity(event_type: str) -> str:
    """Return default severity for an event type. Falls back to 'info'."""
    return EVENT_SEVERITY.get(event_type, INFO)
