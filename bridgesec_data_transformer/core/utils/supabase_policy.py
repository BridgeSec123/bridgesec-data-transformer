"""
Supabase-backed Policy Rule helper.

Replaces core/models/policy_models.py. Stores OPA PolicyRule data in the
`policy_rules` table (see supabase/migrations/001_rbac_schema.sql).
"""
import logging

from core.utils.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

TABLE = "policy_rules"


class SupabasePolicyRule:
    """Lightweight policy rule object backed by a Supabase row."""

    def __init__(self, row: dict):
        self.id          = row.get("id")
        self.policy_id   = row.get("id")   # alias used by OPA / rego_builder callers
        self.name        = row.get("name", "")
        self.description = row.get("description", "")
        self.role        = row.get("role")
        self.entity      = row.get("entity")
        self.action      = row.get("action")
        self.effect      = row.get("effect", "allow")
        self.conditions  = row.get("conditions") or {}
        self.subject_type = row.get("subject_type", "role") or "role"
        self.subject      = row.get("subject")
        self.scope        = row.get("scope")
        self.rego_source = row.get("rego_source")
        self.tenant_id   = row.get("tenant_id")   # None = global (super_admin); set = tenant-specific
        self.created_by  = row.get("created_by")
        self.created_at  = row.get("created_at")
        self.updated_at  = row.get("updated_at")
        self._row        = row

    def to_dict(self) -> dict:
        return {
            "policy_id":   self.id,
            "id":          self.id,
            "name":        self.name,
            "description": self.description,
            "role":        self.role,
            "entity":      self.entity,
            "action":      self.action,
            "effect":      self.effect,
            "conditions":  self.conditions,
            "subject_type": self.subject_type,
            "subject":      self.subject,
            "scope":        self.scope,
            "rego_source": self.rego_source,
            "tenant_id":   self.tenant_id,
            "created_by":  self.created_by,
            "created_at":  self.created_at,
            "updated_at":  self.updated_at,
        }

    # ------------------------------------------------------------------ #
    # Queries                                                              #
    # ------------------------------------------------------------------ #

    @classmethod
    def get_by_id(cls, rule_id: str):
        """Return SupabasePolicyRule by UUID, or None."""
        try:
            result = (
                get_supabase_client()
                .table(TABLE)
                .select("*")
                .eq("id", str(rule_id))
                .limit(1)
                .execute()
            )
            return cls(result.data[0]) if result.data else None
        except Exception as e:
            logger.error(f"SupabasePolicyRule.get_by_id({rule_id}) failed: {e}")
            return None

    @classmethod
    def list_all(cls, role: str = None, page: int = 1, page_size: int = 50, tenant_id: str = None, include_global: bool = True, scope: str = None, subject: str = None):
        """Return paginated (rules, total), optionally filtered by role/scope/subject.

        When tenant_id is provided (non-super-admin callers) only rules that are
        global (tenant_id IS NULL) or belong to that specific tenant are returned.
        Super admin callers pass tenant_id=None to see all rules.

        include_global=False restricts results to tenant-specific rows only (used
        for tenant_admin / backup_admin roles that must not see global policies).

        scope filters the audit marker (role|user|data|user_data); subject filters
        by the targeted user email — used to find fine-grained policies.
        """
        try:
            offset = (page - 1) * page_size
            client = get_supabase_client()

            def _filtered():
                q = client.table(TABLE).select("*", count="exact")
                if role:
                    q = q.eq("role", role)
                if scope:
                    q = q.eq("scope", scope)
                if subject:
                    q = q.eq("subject", subject)
                return q

            if tenant_id is not None:
                if not include_global:
                    # tenant_admin / backup_admin — tenant rows only, no global policies
                    query = _filtered().eq("tenant_id", str(tenant_id))
                    result = query.order("role").range(offset, offset + page_size - 1).execute()
                    return [cls(row) for row in (result.data or [])], (result.count or 0)

                # Fetch global rules (tenant_id IS NULL) + tenant's own rules separately
                # then merge, because Supabase JS SDK doesn't support OR with IS NULL
                # in a single .or_() call cleanly across versions.
                global_q = _filtered().is_("tenant_id", "null")
                tenant_q = _filtered().eq("tenant_id", str(tenant_id))

                global_res = global_q.order("role").execute()
                tenant_res = tenant_q.order("role").execute()

                all_rows  = (global_res.data or []) + (tenant_res.data or [])
                total     = len(all_rows)
                page_rows = all_rows[offset: offset + page_size]
                return [cls(row) for row in page_rows], total

            # Super admin — all rules, no tenant filter
            result = _filtered().order("role").range(offset, offset + page_size - 1).execute()
            return [cls(row) for row in (result.data or [])], (result.count or 0)
        except Exception as e:
            logger.error(f"SupabasePolicyRule.list_all() failed: {e}")
            return [], 0

    @classmethod
    def list_all_raw(cls) -> list:
        """Return all rules as raw dicts (used by rego_builder to compile Rego)."""
        try:
            result = get_supabase_client().table(TABLE).select("*").execute()
            return result.data or []
        except Exception as e:
            logger.error(f"SupabasePolicyRule.list_all_raw() failed: {e}")
            return []

    @classmethod
    def create(cls, data: dict):
        """Insert a new policy rule. Returns the created SupabasePolicyRule."""
        try:
            result = (
                get_supabase_client()
                .table(TABLE)
                .insert(data)
                .execute()
            )
            if result.data:
                return cls(result.data[0])
            raise ValueError("Supabase insert returned no data")
        except Exception as e:
            logger.error(f"SupabasePolicyRule.create() failed: {e}")
            raise

    @classmethod
    def update(cls, rule_id: str, data: dict):
        """Update a policy rule by UUID. Returns updated SupabasePolicyRule."""
        try:
            result = (
                get_supabase_client()
                .table(TABLE)
                .update(data)
                .eq("id", str(rule_id))
                .execute()
            )
            return cls(result.data[0]) if result.data else None
        except Exception as e:
            logger.error(f"SupabasePolicyRule.update({rule_id}) failed: {e}")
            raise

    @classmethod
    def delete(cls, rule_id: str) -> bool:
        """Delete a policy rule by UUID. Returns True if deleted."""
        try:
            result = (
                get_supabase_client()
                .table(TABLE)
                .delete()
                .eq("id", str(rule_id))
                .execute()
            )
            return bool(result.data)
        except Exception as e:
            logger.error(f"SupabasePolicyRule.delete({rule_id}) failed: {e}")
            return False
