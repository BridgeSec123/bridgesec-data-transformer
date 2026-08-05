"""
Supabase-backed User helper.

Replaces MongoDB User model for user storage.
The SupabaseUser class mimics the same interface used across the codebase
(attributes: id, email, username, roles, tenant_id, is_authenticated)
so no other files need major changes when switching from the MongoDB backend.

Supabase table (see supabase/migrations/001_rbac_schema.sql):

    CREATE TABLE public.users (
        id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        username   TEXT NOT NULL,
        email      TEXT NOT NULL UNIQUE,
        password   TEXT,                          -- hashed; NULL for Okta-only users
        roles      JSONB NOT NULL DEFAULT '["user"]',
        tenant_id  TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE INDEX idx_users_email  ON public.users(email);
    CREATE INDEX idx_users_tenant ON public.users(tenant_id);
    CREATE INDEX idx_users_roles  ON public.users USING gin(roles);
"""
import logging

from core.utils.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

TABLE = "users"


class SupabaseUser:
    """Lightweight user object backed by a Supabase row."""

    def __init__(self, row: dict):
        self.id                = row.get("id")
        self.email             = row.get("email")
        self.username          = row.get("username") or row.get("email")
        self.roles             = row.get("roles") or ["user"]   # always a list
        self.tenant_id         = row.get("tenant_id")
        self.password          = row.get("password")
        self.okta_user_id      = row.get("okta_user_id")
        self.app_access_enabled = row.get("app_access_enabled", False)
        self._row              = row

    @property
    def is_authenticated(self):
        return True

    # ------------------------------------------------------------------ #
    # Class-level query helpers                                            #
    # ------------------------------------------------------------------ #

    @classmethod
    def get_all_by_email(cls, email: str, app_access_only: bool = False) -> list:
        """Return all tenant rows for a given email (cross-tenant lookup).

        With app_access_only=True only rows where app_access_enabled=True are returned,
        which is what resolve-tenant and my-tenants use.
        """
        try:
            query = get_supabase_client().table(TABLE).select("*").eq("email", email)
            if app_access_only:
                query = query.eq("app_access_enabled", True)
            result = query.execute()
            return [cls(row) for row in (result.data or [])]
        except Exception as e:
            logger.error(f"SupabaseUser.get_all_by_email({email}) failed: {e}")
            return []

    @classmethod
    def get_by_email(cls, email: str, tenant_id: str = None):
        """Return SupabaseUser for the given email (scoped to tenant when provided), or None."""
        try:
            query = get_supabase_client().table(TABLE).select("*").eq("email", email)
            if tenant_id:
                query = query.eq("tenant_id", tenant_id)
            result = query.limit(1).execute()
            return cls(result.data[0]) if result.data else None
        except Exception as e:
            logger.error(f"SupabaseUser.get_by_email({email}) failed: {e}")
            return None

    @classmethod
    def get_by_id(cls, user_id: str):
        """Return SupabaseUser for the given UUID, or None."""
        try:
            result = (
                get_supabase_client()
                .table(TABLE)
                .select("*")
                .eq("id", str(user_id))
                .limit(1)
                .execute()
            )
            return cls(result.data[0]) if result.data else None
        except Exception as e:
            logger.error(f"SupabaseUser.get_by_id({user_id}) failed: {e}")
            return None

    @classmethod
    def get_by_username(cls, username: str):
        """Return SupabaseUser for the given username, or None."""
        try:
            result = (
                get_supabase_client()
                .table(TABLE)
                .select("*")
                .eq("username", username)
                .limit(1)
                .execute()
            )
            return cls(result.data[0]) if result.data else None
        except Exception as e:
            logger.error(f"SupabaseUser.get_by_username({username}) failed: {e}")
            return None

    @classmethod
    def create_or_update(
        cls,
        email: str,
        username: str,
        roles: list = None,
        tenant_id: str = None,
        # legacy single-role compat — ignored if roles is provided
        role: str = None,
        okta_user_id: str = None,
        app_access_enabled: bool = True,
    ):
        """Upsert a user row by (email, tenant_id). Returns the SupabaseUser instance."""
        if roles is None:
            roles = [role] if role else ["user"]
        try:
            data = {
                "email":               email,
                "username":            username or email,
                "roles":               roles,
                "tenant_id":           tenant_id,
                "okta_user_id":        okta_user_id,
                "app_access_enabled":  app_access_enabled,
            }
            result = (
                get_supabase_client()
                .table(TABLE)
                .upsert(data, on_conflict="email,tenant_id")
                .execute()
            )
            if result.data:
                logger.info(f"Upserted user in Supabase: {email}")
                return cls(result.data[0])
            raise ValueError(f"Supabase upsert returned no data for {email}")
        except Exception as e:
            logger.error(f"SupabaseUser.create_or_update({email}) failed: {e}")
            raise

    def save(self):
        """Persist current state back to Supabase."""
        try:
            data = {
                "email":        self.email,
                "username":     self.username,
                "roles":        self.roles,
                "tenant_id":    self.tenant_id,
                "okta_user_id": getattr(self, "okta_user_id", None),
            }
            client = get_supabase_client()
            if self.id:
                client.table(TABLE).update(data).eq("id", str(self.id)).execute()
            else:
                result = client.table(TABLE).upsert(data, on_conflict="email,tenant_id").execute()
                if result.data:
                    self.id = result.data[0].get("id")
            logger.info(f"Saved user to Supabase: {self.email}")
        except Exception as e:
            logger.error(f"SupabaseUser.save() failed for {self.email}: {e}")
            raise

    @classmethod
    def list_all(cls, page: int = 1, page_size: int = 20, tenant_id: str = None, app_access_only: bool = False):
        """Return paginated (users, total) — optionally scoped to a tenant.

        With app_access_only=True only rows where app_access_enabled=True are returned.
        Role is read directly from each users row (roles JSONB) — no user_tenants join needed.
        """
        try:
            offset = (page - 1) * page_size
            query = get_supabase_client().table(TABLE).select("*", count="exact")
            if tenant_id is not None:
                query = query.eq("tenant_id", str(tenant_id))
            if app_access_only:
                query = query.eq("app_access_enabled", True)
            result = query.range(offset, offset + page_size - 1).execute()
            return [cls(row) for row in (result.data or [])], (result.count or 0)
        except Exception as e:
            logger.error(f"SupabaseUser.list_all() failed: {e}")
            return [], 0

    @classmethod
    def delete_by_id(cls, user_id: str) -> bool:
        """Delete a user by UUID. Returns True if deleted."""
        try:
            result = (
                get_supabase_client()
                .table(TABLE)
                .delete()
                .eq("id", str(user_id))
                .execute()
            )
            return bool(result.data)
        except Exception as e:
            logger.error(f"SupabaseUser.delete_by_id({user_id}) failed: {e}")
            return False

    @classmethod
    def update_roles(cls, user_id: str, roles: list) -> bool:
        """Replace a user's roles list. Returns True on success."""
        try:
            result = (
                get_supabase_client()
                .table(TABLE)
                .update({"roles": roles})
                .eq("id", str(user_id))
                .execute()
            )
            return bool(result.data)
        except Exception as e:
            logger.error(f"SupabaseUser.update_roles({user_id}) failed: {e}")
            return False
