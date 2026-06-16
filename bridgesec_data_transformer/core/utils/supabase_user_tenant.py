"""
Supabase-backed UserTenant helper.

Wraps the user_tenants junction table (see supabase/migrations/007_user_tenants.sql).

    CREATE TABLE public.user_tenants (
        id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id    UUID REFERENCES public.users(id) ON DELETE CASCADE,
        tenant_id  UUID REFERENCES public.tenants(id) ON DELETE CASCADE,
        role       TEXT NOT NULL DEFAULT 'user',
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE(user_id, tenant_id)
    );

This is a service class (no instance state) — all methods are static.
"""
import logging

from core.utils.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

TABLE = "user_tenants"


class SupabaseUserTenant:

    @staticmethod
    def get_tenants_for_user(user_id: str) -> list:
        """
        Return list of SupabaseTenant objects the user has access to (active only).
        Uses a PostgREST join so a single query fetches both tables.
        """
        try:
            result = (
                get_supabase_client()
                .table(TABLE)
                .select("role, tenants(id, name, okta_domain, okta_issuer, is_active)")
                .eq("user_id", str(user_id))
                .execute()
            )
            from core.utils.supabase_tenant import SupabaseTenant
            tenants = []
            for row in (result.data or []):
                tenant_data = row.get("tenants")
                if tenant_data and tenant_data.get("is_active"):
                    tenants.append(SupabaseTenant(tenant_data))
            return tenants
        except Exception as e:
            logger.error(f"SupabaseUserTenant.get_tenants_for_user({user_id}) failed: {e}")
            return []

    @staticmethod
    def get_users_for_tenant(tenant_id: str, page: int = 1, page_size: int = 20) -> tuple:
        """
        Return paginated (rows, total) for all users in a tenant.
        Each row dict contains: role, and a nested 'users' dict with id/email/username/roles.
        """
        try:
            offset = (page - 1) * page_size
            result = (
                get_supabase_client()
                .table(TABLE)
                .select("role, users(id, email, username, roles)", count="exact")
                .eq("tenant_id", str(tenant_id))
                .range(offset, offset + page_size - 1)
                .execute()
            )
            return result.data or [], result.count or 0
        except Exception as e:
            logger.error(f"SupabaseUserTenant.get_users_for_tenant({tenant_id}) failed: {e}")
            return [], 0

    @staticmethod
    def add(user_id: str, tenant_id: str, role: str = "user") -> dict | None:
        """
        Add or update a user's membership in a tenant.
        Upserts on (user_id, tenant_id) so re-inviting is safe.
        Returns the created/updated row dict, or None on failure.
        """
        try:
            result = (
                get_supabase_client()
                .table(TABLE)
                .upsert(
                    {"user_id": str(user_id), "tenant_id": str(tenant_id), "role": role},
                    on_conflict="user_id,tenant_id",
                )
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"SupabaseUserTenant.add({user_id}, {tenant_id}) failed: {e}")
            return None

    @staticmethod
    def remove(user_id: str, tenant_id: str) -> bool:
        """
        Remove a user from a tenant. Returns True if a row was deleted.
        """
        try:
            result = (
                get_supabase_client()
                .table(TABLE)
                .delete()
                .eq("user_id", str(user_id))
                .eq("tenant_id", str(tenant_id))
                .execute()
            )
            return bool(result.data)
        except Exception as e:
            logger.error(f"SupabaseUserTenant.remove({user_id}, {tenant_id}) failed: {e}")
            return False

    @staticmethod
    def get_role(user_id: str, tenant_id: str) -> str | None:
        """
        Return the user's role in the given tenant, or None if not a member.
        """
        try:
            result = (
                get_supabase_client()
                .table(TABLE)
                .select("role")
                .eq("user_id", str(user_id))
                .eq("tenant_id", str(tenant_id))
                .limit(1)
                .execute()
            )
            return result.data[0]["role"] if result.data else None
        except Exception as e:
            logger.error(f"SupabaseUserTenant.get_role({user_id}, {tenant_id}) failed: {e}")
            return None
