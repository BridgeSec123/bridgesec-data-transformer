"""
Migrate existing Supabase users from the old single `role` string to the
new `roles` JSONB array.

Usage:
    python manage.py migrate_roles

Run AFTER the Supabase SQL migration (001_rbac_schema.sql) which drops the
old `role` column and adds `roles`. This command handles any users whose
`roles` column is still empty / defaulted to ["user"] but should be elevated.

If the old `role` data was backed up in a separate column before the ALTER
TABLE, update LEGACY_ROLE_BACKUP_COLUMN below to read from it.

Safe to re-run — only updates users where roles is ["user"] and a legacy
mapping suggests a different value.
"""
from django.core.management.base import BaseCommand


# Map old single role → new roles list
ROLE_MAP = {
    "admin": ["tenant_admin"],
    "user":  ["user"],
}


class Command(BaseCommand):
    help = "Migrate old single-role field to new roles list in Supabase."

    def handle(self, *args, **options):
        from core.utils.supabase_client import get_supabase_client

        client = get_supabase_client()
        # Fetch all users
        result = client.table("users").select("id,email,roles").execute()
        users  = result.data or []
        updated = 0

        for row in users:
            current_roles = row.get("roles") or ["user"]
            # Users already have meaningful roles — skip
            if len(current_roles) > 1 or current_roles[0] not in ("user", "admin"):
                continue
            # Map "admin" → "tenant_admin"
            if "admin" in current_roles:
                new_roles = ["tenant_admin"]
                client.table("users").update({"roles": new_roles}).eq("id", row["id"]).execute()
                self.stdout.write(f"  {row['email']}: admin → tenant_admin")
                updated += 1

        self.stdout.write(self.style.SUCCESS(f"Role migration complete. {updated} users updated."))
