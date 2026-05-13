"""
Supabase-backed Tenant helper.

Replaces the MongoDB Tenant model. All tenant configuration lives in
the Supabase `tenants` table (see supabase/migrations/001_rbac_schema.sql).
"""
import logging

from core.utils.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

TABLE = "tenants"


class SupabaseTenant:
    """Lightweight tenant object backed by a Supabase row."""

    def __init__(self, row: dict):
        self.id                   = row.get("id")
        self.name                 = row.get("name")
        self.okta_domain          = row.get("okta_domain")
        self.okta_client_id       = row.get("okta_client_id")
        self.okta_client_secret   = row.get("okta_client_secret")
        self.okta_issuer          = row.get("okta_issuer")
        self.mongo_uri            = row.get("mongo_uri")
        self.mongo_db_prefix      = row.get("mongo_db_prefix")
        self.terraform_server_url = row.get("terraform_server_url")
        self.terraform_state_path = row.get("terraform_state_path")
        # Optional: per-tenant Supabase instance for complete data isolation.
        # When blank the master Supabase (from .env) is used instead.
        self.supabase_url         = row.get("supabase_url")
        self.supabase_key         = row.get("supabase_key")
        self.service_client_id    = row.get("service_client_id")
        self.service_private_key  = row.get("service_private_key")
        self.service_scopes       = row.get("service_scopes")
        self.is_active            = row.get("is_active", True)
        self.created_at           = row.get("created_at")
        self._row                 = row

    # ------------------------------------------------------------------ #
    # Queries                                                              #
    # ------------------------------------------------------------------ #

    @classmethod
    def get_by_id(cls, tenant_id: str):
        """Return SupabaseTenant for the given UUID, or None."""
        try:
            result = (
                get_supabase_client()
                .table(TABLE)
                .select("*")
                .eq("id", str(tenant_id))
                .limit(1)
                .execute()
            )
            return cls(result.data[0]) if result.data else None
        except Exception as e:
            logger.error(f"SupabaseTenant.get_by_id({tenant_id}) failed: {e}")
            return None

    @classmethod
    def get_by_okta_domain(cls, okta_domain: str):
        """Return SupabaseTenant matching the given Okta domain, or None."""
        try:
            result = (
                get_supabase_client()
                .table(TABLE)
                .select("*")
                .eq("okta_domain", okta_domain)
                .eq("is_active", True)
                .limit(1)
                .execute()
            )
            return cls(result.data[0]) if result.data else None
        except Exception as e:
            logger.error(f"SupabaseTenant.get_by_okta_domain({okta_domain}) failed: {e}")
            return None

    @classmethod
    def list_all(cls, active_only: bool = True, page: int = 1, page_size: int = 50):
        """Return paginated (tenants, total)."""
        try:
            offset = (page - 1) * page_size
            query = get_supabase_client().table(TABLE).select("*", count="exact")
            if active_only:
                query = query.eq("is_active", True)
            result = query.range(offset, offset + page_size - 1).execute()
            return [cls(row) for row in (result.data or [])], (result.count or 0)
        except Exception as e:
            logger.error(f"SupabaseTenant.list_all() failed: {e}")
            return [], 0

    @classmethod
    def create(cls, data: dict):
        """Insert a new tenant row. Returns the created SupabaseTenant."""
        try:
            result = (
                get_supabase_client()
                .table(TABLE)
                .insert(data)
                .execute()
            )
            if result.data:
                logger.info(f"Created tenant: {data.get('name')}")
                return cls(result.data[0])
            raise ValueError("Supabase insert returned no data")
        except Exception as e:
            logger.error(f"SupabaseTenant.create() failed: {e}")
            raise

    @classmethod
    def update(cls, tenant_id: str, data: dict):
        """Update tenant fields. Returns updated SupabaseTenant."""
        try:
            result = (
                get_supabase_client()
                .table(TABLE)
                .update(data)
                .eq("id", str(tenant_id))
                .execute()
            )
            if result.data:
                return cls(result.data[0])
            return None
        except Exception as e:
            logger.error(f"SupabaseTenant.update({tenant_id}) failed: {e}")
            raise

    @classmethod
    def soft_delete(cls, tenant_id: str) -> bool:
        """Set is_active=False. Returns True on success."""
        try:
            result = (
                get_supabase_client()
                .table(TABLE)
                .update({"is_active": False})
                .eq("id", str(tenant_id))
                .execute()
            )
            return bool(result.data)
        except Exception as e:
            logger.error(f"SupabaseTenant.soft_delete({tenant_id}) failed: {e}")
            return False
