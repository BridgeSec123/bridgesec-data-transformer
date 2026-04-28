import types
import uuid
from datetime import datetime, timezone

from django.core.management.base import BaseCommand

from core.models.policy_models import PolicyRule
from core.services import opa_client, rego_builder


# Three seed rules needed because Okta auto-provisioning hardcodes role="admin"
# and there is no role update UI — we need admin-everything to bootstrap access,
# user-read-only for downgraded accounts, and admin-role-management to gate
# PATCH /api/users/<id>/role/ behind admin role.
SEEDS = [
    {
        "name": "admin-everything",
        "description": "Admins can perform any action on any entity.",
        "role": "admin",
        "entity": "*",
        "action": "*",
        "effect": "allow",
        "conditions": {},
    },
    {
        "name": "user-read-only",
        "description": "Regular users can only read any entity.",
        "role": "user",
        "entity": "*",
        "action": "read",
        "effect": "allow",
        "conditions": {},
    },
    {
        "name": "admin-role-management",
        "description": "Only admins can update user roles.",
        "role": "admin",
        "entity": "users",
        "action": "update",
        "effect": "allow",
        "conditions": {},
    },
]


class Command(BaseCommand):
    help = "Bootstrap seed OPA policies (admin-everything, user-read-only, admin-role-management)."

    def handle(self, *args, **options):
        for seed in SEEDS:
            existing = PolicyRule.objects.filter(name=seed["name"]).first()
            if existing:
                self.stdout.write(f"Exists: {seed['name']} (policy_id={existing.policy_id})")
                continue

            rule_stub = types.SimpleNamespace(policy_id=str(uuid.uuid4()), **seed)
            rego_text = rego_builder.translate(rule_stub)
            now = datetime.now(timezone.utc)

            rule = PolicyRule(
                policy_id   = rule_stub.policy_id,
                rego_source = rego_text,
                created_by  = "system",
                created_at  = now,
                updated_at  = now,
                **seed,
            )
            rule.save()

            try:
                opa_client.push_policy(rule.policy_id, rego_text)
                self.stdout.write(self.style.SUCCESS(
                    f"Created: {seed['name']} (policy_id={rule.policy_id}) → pushed to OPA"
                ))
            except Exception as e:
                self.stdout.write(self.style.WARNING(
                    f"Created in Mongo but OPA push failed for {seed['name']}: {e}"
                ))

        self.stdout.write(self.style.SUCCESS("Seed policies ready."))
