"""
Supabase-backed Role helper.

Wraps the `roles` table (see supabase/migrations/001_rbac_schema.sql).
System roles (is_system=True) cannot be deleted or renamed.
"""
import logging

from core.utils.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

TABLE = "roles"


class SupabaseRole:
    """Lightweight role object backed by a Supabase row."""

    def __init__(self, row: dict):
        self.id           = row.get("id")
        self.name         = row.get("name")
        self.display_name = row.get("display_name")
        self.description  = row.get("description")
        self.is_system    = row.get("is_system", False)
        self.tenant_id    = row.get("tenant_id")
        self.created_at   = row.get("created_at")
        self.created_by   = row.get("created_by")
        self.permissions  = row.get("permissions") or []

    # ------------------------------------------------------------------ #
    # Queries                                                              #
    # ------------------------------------------------------------------ #

    @classmethod
    def get_by_name(cls, name: str):
        """Return SupabaseRole by unique name, or None."""
        try:
            result = (
                get_supabase_client()
                .table(TABLE)
                .select("*")
                .eq("name", name)
                .limit(1)
                .execute()
            )
            return cls(result.data[0]) if result.data else None
        except Exception as e:
            logger.error(f"SupabaseRole.get_by_name({name}) failed: {e}")
            return None

    @classmethod
    def get_by_id(cls, role_id: str):
        """Return SupabaseRole by UUID, or None."""
        try:
            result = (
                get_supabase_client()
                .table(TABLE)
                .select("*")
                .eq("id", str(role_id))
                .limit(1)
                .execute()
            )
            return cls(result.data[0]) if result.data else None
        except Exception as e:
            logger.error(f"SupabaseRole.get_by_id({role_id}) failed: {e}")
            return None

    @classmethod
    def list_all(cls, tenant_id: str = None):
        """
        Return all roles visible in a context.
        - Global roles (tenant_id IS NULL) are always included.
        - If tenant_id is provided, also include that tenant's custom roles.
        """
        try:
            client = get_supabase_client()
            if tenant_id:
                # global roles + this tenant's custom roles
                result = (
                    client.table(TABLE)
                    .select("*")
                    .or_(f"tenant_id.is.null,tenant_id.eq.{tenant_id}")
                    .order("name")
                    .execute()
                )
            else:
                # global roles only (super admin context)
                result = (
                    client.table(TABLE)
                    .select("*")
                    .is_("tenant_id", "null")
                    .order("name")
                    .execute()
                )
            return [cls(row) for row in (result.data or [])]
        except Exception as e:
            logger.error(f"SupabaseRole.list_all() failed: {e}")
            return []

    @classmethod
    def create(cls, data: dict):
        """Insert a new role. Returns the created SupabaseRole."""
        try:
            result = (
                get_supabase_client()
                .table(TABLE)
                .insert(data)
                .execute()
            )
            if result.data:
                logger.info(f"Created role: {data.get('name')}")
                return cls(result.data[0])
            raise ValueError("Supabase insert returned no data")
        except Exception as e:
            logger.error(f"SupabaseRole.create() failed: {e}")
            raise

    @classmethod
    def update(cls, name: str, data: dict):
        """
        Update a role by name. Raises ValueError if the role is a system role
        and the caller tries to change is_system or name fields.
        """
        role = cls.get_by_name(name)
        if role and role.is_system and ("name" in data or "is_system" in data):
            raise ValueError(f"Cannot modify protected fields on system role '{name}'")
        try:
            result = (
                get_supabase_client()
                .table(TABLE)
                .update(data)
                .eq("name", name)
                .execute()
            )
            return cls(result.data[0]) if result.data else None
        except Exception as e:
            logger.error(f"SupabaseRole.update({name}) failed: {e}")
            raise

    @classmethod
    def delete(cls, name: str) -> bool:
        """
        Delete a role by name. Raises ValueError for system roles.
        Returns True if deleted.
        """
        role = cls.get_by_name(name)
        if not role:
            return False
        if role.is_system:
            raise ValueError(f"Cannot delete system role '{name}'")
        try:
            result = (
                get_supabase_client()
                .table(TABLE)
                .delete()
                .eq("name", name)
                .execute()
            )
            return bool(result.data)
        except Exception as e:
            logger.error(f"SupabaseRole.delete({name}) failed: {e}")
            return False

