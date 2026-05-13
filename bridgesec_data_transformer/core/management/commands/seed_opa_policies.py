"""
Seed default OPA policies for each system role into Supabase and push to OPA.

Usage:
    python manage.py seed_opa_policies

Safe to re-run — upserts by (role, entity, action).
"""
import uuid
from django.core.management.base import BaseCommand

# Default allow rules per role.
# Format: (role, entity, action, effect, conditions_dict)
DEFAULT_POLICIES = [
    # ── admin: full access (same as tenant_admin) ────────────────────────
    ("admin", "*", "read",   "allow", {}),
    ("admin", "*", "create", "allow", {}),
    ("admin", "*", "update", "allow", {}),
    ("admin", "*", "delete", "allow", {}),

    # ── user: read-only access to everything ─────────────────────────────
    ("user", "*", "read",   "allow", {}),
    ("user", "*", "create", "deny",  {}),
    ("user", "*", "update", "deny",  {}),
    ("user", "*", "delete", "deny",  {}),

    # ── tenant_admin: all actions within tenant ──────────────────────────
    ("tenant_admin", "*", "read",   "allow", {}),
    ("tenant_admin", "*", "create", "allow", {}),
    ("tenant_admin", "*", "update", "allow", {}),
    ("tenant_admin", "*", "delete", "allow", {}),

    # ── backup_admin: read + trigger backup only ─────────────────────────
    # Can read all snapshots and entity data.
    # Can trigger a new bulk backup (POST /api/bulk/).
    # Cannot restore, create, update, or delete any Okta entity.
    ("backup_admin", "*",    "read",   "allow", {}),
    ("backup_admin", "bulk", "create", "allow", {}),
    ("backup_admin", "*",    "create", "deny",  {}),
    ("backup_admin", "*",    "update", "deny",  {}),
    ("backup_admin", "*",    "delete", "deny",  {}),

    # ── restore_viewer: read only ─────────────────────────────────────────
    ("restore_viewer", "*", "read",   "allow", {}),
    ("restore_viewer", "*", "create", "deny",  {}),
    ("restore_viewer", "*", "update", "deny",  {}),
    ("restore_viewer", "*", "delete", "deny",  {}),

    # ── policy_admin: manage policies + read ─────────────────────────────
    ("policy_admin", "*",        "read",   "allow", {}),
    ("policy_admin", "policies", "create", "allow", {}),
    ("policy_admin", "policies", "update", "allow", {}),
    ("policy_admin", "policies", "delete", "allow", {}),
    ("policy_admin", "*",        "create", "deny",  {}),
    ("policy_admin", "*",        "update", "deny",  {}),
    ("policy_admin", "*",        "delete", "deny",  {}),

    # ── config_admin: tenant config + read ───────────────────────────────
    ("config_admin", "*",        "read",   "allow", {}),
    ("config_admin", "tenants",  "update", "allow", {}),
    ("config_admin", "*",        "create", "deny",  {}),
    ("config_admin", "*",        "delete", "deny",  {}),

    # ── entity_config_admin: entity config + read ─────────────────────────
    ("entity_config_admin", "*",             "read",   "allow", {}),
    ("entity_config_admin", "entity_config", "update", "allow", {}),
    ("entity_config_admin", "*",             "create", "deny",  {}),
    ("entity_config_admin", "*",             "delete", "deny",  {}),

    # ── read_only_admin: read, diff, compare — no writes ─────────────────
    ("read_only_admin", "*", "read",   "allow", {}),
    ("read_only_admin", "*", "create", "deny",  {}),
    ("read_only_admin", "*", "update", "deny",  {}),
    ("read_only_admin", "*", "delete", "deny",  {}),
]


class Command(BaseCommand):
    help = "Seed default OPA policy rules for system roles into Supabase and push to OPA."

    def handle(self, *args, **options):
        from core.utils.supabase_client import get_supabase_client
        from core.services import opa_client, rego_builder
        import types

        sb = get_supabase_client()

        # Push base aggregation policy first
        opa_client.push_policy("base", rego_builder.BASE_REGO)
        self.stdout.write("Pushed base Rego policy.")

        seeded = 0
        for role, entity, action, effect, conditions in DEFAULT_POLICIES:
            policy_id = str(uuid.uuid4())

            rule_ns = types.SimpleNamespace(
                policy_id=policy_id,
                name=f"{role}_{entity}_{action}",
                description="",
                role=role,
                entity=entity,
                action=action,
                effect=effect,
                conditions=conditions,
            )
            rego_text = rego_builder.translate(rule_ns)

            data = {
                "id":          policy_id,
                "name":        f"{role}_{entity}_{action}",
                "role":        role,
                "entity":      entity,
                "action":      action,
                "effect":      effect,
                "conditions":  conditions,
                "rego_source": rego_text,
            }
            # Upsert by (role, entity, action, effect) composite — not natively supported
            # so we insert and skip on duplicate via try/except
            try:
                sb.table("policy_rules").insert(data).execute()
                opa_client.push_policy(policy_id, rego_text)
                seeded += 1
            except Exception as e:
                if "duplicate" in str(e).lower() or "unique" in str(e).lower():
                    self.stdout.write(f"  skip (exists): {role}/{entity}/{action}/{effect}")
                else:
                    self.stdout.write(self.style.WARNING(f"  error: {role}/{entity}/{action}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"Seeded {seeded} OPA policy rules."))
