"""Role -> permission-name lookup, backed directly by Supabase `roles.permissions`.

No caching: every call queries Supabase fresh, so a permission change made via
the role-permission API (core/views/role_viewset.py) takes effect on the very
next request, across every worker process, with no invalidation to coordinate.
"""
import logging

from core.utils.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


def get_permissions_for_roles(role_names):
    """Union of `permissions` across every role in `role_names`.

    Deliberately unfiltered by tenant_id (unlike SupabaseRole.list_all(),
    which scopes for UI visibility) — a caller's roles can include a
    tenant-scoped custom role, so resolution must see every role by name.
    """
    if not role_names:
        return set()
    try:
        rows = (
            get_supabase_client()
            .table("roles")
            .select("permissions")
            .in_("name", list(role_names))
            .execute()
        ).data or []
    except Exception as e:
        logger.error(f"get_permissions_for_roles({role_names}) failed: {e}")
        return set()  # Supabase unreachable -> empty grant set -> deny
    return set().union(*(set(r.get("permissions") or []) for r in rows)) if rows else set()
