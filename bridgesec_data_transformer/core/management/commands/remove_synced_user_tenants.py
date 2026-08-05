"""
Management command: remove user_tenants rows that were bulk-added by the
sync_users_from_snapshot command.

The sync inserted user_tenants rows for every Okta user (identified by
users.okta_user_id IS NOT NULL) under a tenant.  This command reverses
that — it deletes those junction rows while leaving the users table intact.

Usage:
    # Remove for all tenants (dry-run preview first)
    python manage.py remove_synced_user_tenants --dry-run
    python manage.py remove_synced_user_tenants

    # Remove for one specific tenant only
    python manage.py remove_synced_user_tenants --tenant-id <uuid>
    python manage.py remove_synced_user_tenants --tenant-id <uuid> --dry-run
"""
import logging

from django.conf import settings
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Delete user_tenants rows added by the Okta snapshot sync"

    def add_arguments(self, parser):
        parser.add_argument(
            "--tenant-id",
            help="Limit deletion to this tenant UUID. Omit to process all active tenants.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show counts without deleting anything.",
        )

    def handle(self, *args, **options):
        tenant_id_arg = options.get("tenant_id")
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — nothing will be deleted\n"))

        from core.utils.supabase_client import get_supabase_client
        sb = get_supabase_client()

        tenant_ids = self._collect_tenant_ids(tenant_id_arg)
        if not tenant_ids:
            self.stdout.write(self.style.WARNING("No tenants found to process."))
            return

        self.stdout.write(f"Processing {len(tenant_ids)} tenant(s)...\n")

        total_deleted = 0

        for tid in tenant_ids:
            count = self._remove_for_tenant(sb, tid, dry_run)
            label = "would delete" if dry_run else "deleted"
            self.stdout.write(self.style.SUCCESS(
                f"  tenant={tid}  →  {label} {count} user_tenants row(s)"
            ))
            total_deleted += count

        self.stdout.write("")
        action = "Would delete" if dry_run else "Deleted"
        self.stdout.write(self.style.SUCCESS(
            f"{action} {total_deleted} user_tenants row(s) in total."
        ))

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _collect_tenant_ids(self, filter_id):
        """Return list of tenant UUID strings to process."""
        if filter_id:
            return [filter_id]

        multi = getattr(settings, 'MULTI_TENANCY_ENABLED', False)
        if not multi:
            self.stdout.write(self.style.WARNING(
                "MULTI_TENANCY_ENABLED is False — specify --tenant-id explicitly."
            ))
            return []

        try:
            from core.utils.supabase_tenant import SupabaseTenant
            ids = []
            page, page_size = 1, 100
            while True:
                tenants, total = SupabaseTenant.list_all(
                    active_only=True, page=page, page_size=page_size
                )
                ids.extend(str(t.id) for t in tenants)
                if page * page_size >= total:
                    break
                page += 1
            return ids
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"Failed to list tenants: {exc}"))
            return []

    def _remove_for_tenant(self, sb, tenant_id, dry_run):
        """
        Delete (or count) user_tenants rows for users whose okta_user_id IS NOT NULL
        under this tenant.
        """
        try:
            # Find user UUIDs that were created by the sync (have okta_user_id set).
            resp = (
                sb.table("users")
                .select("id")
                .not_.is_("okta_user_id", "null")
                .execute()
            )
            user_ids = [row["id"] for row in (resp.data or []) if row.get("id")]

            if not user_ids:
                return 0

            if dry_run:
                # Count matching rows without deleting.
                count_resp = (
                    sb.table("user_tenants")
                    .select("id", count="exact")
                    .eq("tenant_id", str(tenant_id))
                    .in_("user_id", user_ids)
                    .execute()
                )
                return count_resp.count or 0

            # Delete in batches to stay within Supabase URL length limits.
            deleted = 0
            batch_size = 500
            for i in range(0, len(user_ids), batch_size):
                batch = user_ids[i:i + batch_size]
                del_resp = (
                    sb.table("user_tenants")
                    .delete()
                    .eq("tenant_id", str(tenant_id))
                    .in_("user_id", batch)
                    .execute()
                )
                deleted += len(del_resp.data or [])
            return deleted

        except Exception as exc:
            self.stderr.write(self.style.ERROR(
                f"  Error processing tenant {tenant_id}: {exc}"
            ))
            return 0
