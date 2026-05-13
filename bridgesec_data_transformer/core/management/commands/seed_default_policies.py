"""
Seed baseline OPA allow-rules for all standard roles.

OPA defaults to deny-all. Without at least one seeded policy rule that fires
allow for (role, entity, action), every authenticated non-super-admin request
to endpoints covered by OPAPermission returns 403.

This command is idempotent: it skips any policy whose name already exists in
Supabase unless --force is passed (which deletes + re-creates it).

Usage:
    python manage.py seed_default_policies
    python manage.py seed_default_policies --force
"""

import types
import uuid
from datetime import datetime, timezone

from django.core.management.base import BaseCommand


# ---------------------------------------------------------------------------
# Policy definitions
# ---------------------------------------------------------------------------

# entity="*" → no entity condition in Rego → matches any entity name.
# entity="bulk" → only matches BulkEntityViewSet requests (db-map, resources, data, …).
#
# How OPA resolves (entity, action) per endpoint:
#   GET  /db-map/                              → entity=bulk,        action=read
#   GET  /resources/                           → entity=bulk,        action=read
#   GET  /data/                                → entity=bulk,        action=read
#   POST /api/bulk/                            → entity=bulk,        action=create
#   GET  /diff-collections/<e>/                → entity=<e>,         action=read
#   GET  /entity-schema/<e>/                   → entity=<e>,         action=read
#   POST /restore/<db>/<e>/                    → entity=<e>,         action=create
#   POST /restore/<db>/<e>/?operation_type=restore → entity=<e>,    action=update
#   POST /restore/<db>/<e>/?operation_type=delete  → entity=<e>,    action=delete
#   POST /confirm-delete/?action=confirm       → entity=bulk,        action=delete

DEFAULT_POLICIES = [
    # ── tenant_admin: full read + write on own tenant's Okta data ──────────
    {
        "name":        "tenant_admin: read bulk",
        "description": "Allows tenant_admin to read snapshot data (db-map, data, resources, progress).",
        "role":        "tenant_admin",
        "entity":      "bulk",
        "action":      "read",
        "effect":      "allow",
    },
    {
        "name":        "tenant_admin: trigger bulk fetch",
        "description": "Allows tenant_admin to trigger a new snapshot (POST /api/bulk/).",
        "role":        "tenant_admin",
        "entity":      "bulk",
        "action":      "create",
        "effect":      "allow",
    },
    {
        "name":        "tenant_admin: read entities",
        "description": "Allows tenant_admin to read any entity (diff-collections, entity-schema).",
        "role":        "tenant_admin",
        "entity":      "*",
        "action":      "read",
        "effect":      "allow",
    },
    {
        "name":        "tenant_admin: create Okta resource",
        "description": "Allows tenant_admin to create new Okta resources via /restore/.",
        "role":        "tenant_admin",
        "entity":      "*",
        "action":      "create",
        "effect":      "allow",
    },
    {
        "name":        "tenant_admin: restore Okta resource",
        "description": "Allows tenant_admin to restore (update) Okta resources via /restore/?operation_type=restore.",
        "role":        "tenant_admin",
        "entity":      "*",
        "action":      "update",
        "effect":      "allow",
    },
    {
        "name":        "tenant_admin: delete Okta resource",
        "description": "Allows tenant_admin to delete Okta resources via /restore/?operation_type=delete and /confirm-delete/.",
        "role":        "tenant_admin",
        "entity":      "*",
        "action":      "delete",
        "effect":      "allow",
    },

    # ── backup_admin: read + bulk fetch only; restore/create/delete denied ─
    {
        "name":        "backup_admin: read bulk",
        "description": "Allows backup_admin to read snapshot data (db-map, data, resources).",
        "role":        "backup_admin",
        "entity":      "bulk",
        "action":      "read",
        "effect":      "allow",
    },
    {
        "name":        "backup_admin: trigger bulk fetch",
        "description": "Allows backup_admin to trigger a new snapshot (POST /api/bulk/).",
        "role":        "backup_admin",
        "entity":      "bulk",
        "action":      "create",
        "effect":      "allow",
    },
    {
        "name":        "backup_admin: read entities",
        "description": "Allows backup_admin to read any entity (diff-collections, entity-schema).",
        "role":        "backup_admin",
        "entity":      "*",
        "action":      "read",
        "effect":      "allow",
    },
    # NOTE: no update/delete rules for backup_admin → OPA denies restore/delete by default.

    # ── admin: same as tenant_admin ─────────────────────────────────────────
    {
        "name":        "admin: read bulk",
        "description": "Allows admin to read snapshot data.",
        "role":        "admin",
        "entity":      "bulk",
        "action":      "read",
        "effect":      "allow",
    },
    {
        "name":        "admin: trigger bulk fetch",
        "description": "Allows admin to trigger a new snapshot.",
        "role":        "admin",
        "entity":      "bulk",
        "action":      "create",
        "effect":      "allow",
    },
    {
        "name":        "admin: read entities",
        "description": "Allows admin to read any entity.",
        "role":        "admin",
        "entity":      "*",
        "action":      "read",
        "effect":      "allow",
    },
    {
        "name":        "admin: create Okta resource",
        "description": "Allows admin to create new Okta resources.",
        "role":        "admin",
        "entity":      "*",
        "action":      "create",
        "effect":      "allow",
    },
    {
        "name":        "admin: restore Okta resource",
        "description": "Allows admin to restore (update) Okta resources.",
        "role":        "admin",
        "entity":      "*",
        "action":      "update",
        "effect":      "allow",
    },
    {
        "name":        "admin: delete Okta resource",
        "description": "Allows admin to delete Okta resources.",
        "role":        "admin",
        "entity":      "*",
        "action":      "delete",
        "effect":      "allow",
    },

    # ── user: read-only ──────────────────────────────────────────────────────
    {
        "name":        "user: read bulk",
        "description": "Allows user role to view snapshot data (read-only).",
        "role":        "user",
        "entity":      "bulk",
        "action":      "read",
        "effect":      "allow",
    },
    {
        "name":        "user: read entities",
        "description": "Allows user role to read any entity (read-only).",
        "role":        "user",
        "entity":      "*",
        "action":      "read",
        "effect":      "allow",
    },
]


def _find_existing(name: str):
    """Return existing SupabasePolicyRule whose name matches, or None."""
    from core.utils.supabase_client import get_supabase_client
    result = (
        get_supabase_client()
        .table("policy_rules")
        .select("*")
        .eq("name", name)
        .limit(1)
        .execute()
    )
    if result.data:
        from core.utils.supabase_policy import SupabasePolicyRule
        return SupabasePolicyRule(result.data[0])
    return None


class Command(BaseCommand):
    help = "Seed baseline OPA allow-rules for tenant_admin, backup_admin, admin, and user roles."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            default=False,
            help="Delete and re-create policies that already exist.",
        )

    def handle(self, *args, **options):
        from core.utils.supabase_policy import SupabasePolicyRule
        from core.services import opa_client, opa_sync, rego_builder

        force = options["force"]
        created = skipped = failed = 0
        opa_reachable = True

        # Quick OPA reachability check
        try:
            opa_client.list_policies()
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(
                    f"OPA unreachable ({e}). Policies will be saved to Supabase only. "
                    "Run 'Resync OPA' from the Policies UI after OPA comes back online."
                )
            )
            opa_reachable = False

        for entry in DEFAULT_POLICIES:
            name = entry["name"]
            try:
                existing = _find_existing(name)

                if existing and not force:
                    self.stdout.write(f"  SKIP  {name}")
                    skipped += 1
                    continue

                # --force: remove existing rule first
                if existing and force:
                    if opa_reachable:
                        try:
                            opa_client.delete_policy(str(existing.id))
                        except Exception:
                            pass
                    SupabasePolicyRule.delete(str(existing.id))

                # Build rule namespace (mirrors PolicyRuleSerializer.create logic)
                policy_id = str(uuid.uuid4())
                now = datetime.now(timezone.utc).isoformat()
                rule_ns = types.SimpleNamespace(
                    policy_id=policy_id,
                    tenant_id=None,          # global — applies to all tenants
                    name=entry["name"],
                    description=entry.get("description", ""),
                    role=entry["role"],
                    entity=entry["entity"],
                    action=entry["action"],
                    effect=entry["effect"],
                    conditions={},
                    created_by="seed_default_policies",
                    created_at=now,
                    updated_at=now,
                )
                rego_text = rego_builder.translate(rule_ns)

                rule = SupabasePolicyRule.create({
                    "id":          policy_id,
                    "name":        entry["name"],
                    "description": entry.get("description", ""),
                    "role":        entry["role"],
                    "entity":      entry["entity"],
                    "action":      entry["action"],
                    "effect":      entry["effect"],
                    "conditions":  {},
                    "rego_source": rego_text,
                    "tenant_id":   None,
                    "created_by":  "seed_default_policies",
                    "created_at":  now,
                    "updated_at":  now,
                })

                if opa_reachable:
                    try:
                        opa_client.push_policy(str(rule.id), rego_text)
                    except Exception as e:
                        self.stdout.write(
                            self.style.WARNING(f"  WARN  {name} saved to Supabase but OPA push failed: {e}")
                        )

                label = "CREATE" if not (existing and force) else "FORCE "
                self.stdout.write(self.style.SUCCESS(f"  {label}  {name}"))
                created += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  FAIL  {name}: {e}"))
                failed += 1

        # Full OPA reconcile at the end
        if opa_reachable:
            try:
                result = opa_sync.sync_from_mongo()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\nOPA sync complete — {result['synced']} synced, "
                        f"{result['removed_orphans']} orphans removed."
                    )
                )
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"\nOPA sync failed: {e}"))

        style = self.style.SUCCESS if failed == 0 else self.style.ERROR
        self.stdout.write(
            style(
                f"\nSummary: {created} created, {skipped} skipped, {failed} failed "
                f"(total {len(DEFAULT_POLICIES)} policies)."
            )
        )
