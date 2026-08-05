"""
Management command: sync Okta users from existing MongoDB snapshots into Supabase.

Runs the same logic as the post-bulk Celery task (sync_okta_users_to_supabase)
but synchronously in the foreground so you can see results immediately without
triggering a new bulk fetch.

Usage:
    # Sync the latest snapshot for every active tenant (default)
    python manage.py sync_users_from_snapshot

    # Sync a specific snapshot DB for a specific tenant
    python manage.py sync_users_from_snapshot --db-name acme_2026-06-09T1045 --tenant-id <uuid>

    # Preview counts without writing anything
    python manage.py sync_users_from_snapshot --dry-run
"""
import logging

from django.conf import settings
from django.core.management.base import BaseCommand
from pymongo import MongoClient

logger = logging.getLogger(__name__)

BATCH_SIZE = 500


class Command(BaseCommand):
    help = "Sync Okta users from MongoDB snapshots into the Supabase users table"

    def add_arguments(self, parser):
        parser.add_argument(
            "--db-name",
            help="Explicit MongoDB snapshot DB name to sync from (e.g. acme_2026-06-09T1045). "
                 "If omitted, the latest snapshot for each tenant is used.",
        )
        parser.add_argument(
            "--tenant-id",
            help="Process only this tenant UUID. Required when --db-name is provided.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Count users without writing to Supabase.",
        )

    def handle(self, *args, **options):
        db_name_arg = options.get("db_name")
        tenant_id_arg = options.get("tenant_id")
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — nothing will be written to Supabase\n"))

        # ── Build the list of (tenant, db_name, mongo_uri) tuples to process ──
        jobs = []

        if db_name_arg:
            if not tenant_id_arg:
                self.stderr.write(self.style.ERROR(
                    "--tenant-id is required when --db-name is provided"
                ))
                return
            mongo_uri = self._resolve_mongo_uri(tenant_id_arg)
            jobs.append((tenant_id_arg, db_name_arg, mongo_uri))
        else:
            jobs = self._discover_jobs(tenant_id_arg)

        if not jobs:
            self.stdout.write(self.style.WARNING("No snapshots found to process."))
            return

        self.stdout.write(f"Processing {len(jobs)} tenant snapshot(s)...\n")

        total_inserted = 0
        total_present = 0

        for tenant_id, db_name, mongo_uri in jobs:
            self.stdout.write(f"  tenant={tenant_id}  db={db_name}")
            result = self._sync_one(tenant_id, db_name, mongo_uri, dry_run)
            status = result.get("status")
            if status == "skipped":
                self.stdout.write(self.style.WARNING(
                    f"    → SKIPPED: {result.get('reason')}"
                ))
            elif status == "error":
                self.stdout.write(self.style.ERROR(
                    f"    → ERROR: {result.get('reason')}"
                ))
            else:
                ins = result.get("inserted", 0)
                pres = result.get("already_present", 0)
                total_inserted += ins
                total_present += pres
                self.stdout.write(self.style.SUCCESS(
                    f"    → inserted={ins}  already_present={pres}"
                ))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Done.  Total inserted={total_inserted}  already_present={total_present}"
        ))

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _resolve_mongo_uri(self, tenant_id):
        """Return the mongo_uri for the given tenant, or the system URI."""
        if tenant_id and getattr(settings, 'MULTI_TENANCY_ENABLED', False):
            try:
                from core.utils.supabase_tenant import SupabaseTenant
                tenant = SupabaseTenant.get_by_id(tenant_id)
                if tenant and tenant.mongo_uri:
                    return tenant.mongo_uri
            except Exception as exc:
                logger.warning(f"Could not resolve tenant {tenant_id}: {exc}")
        return getattr(settings, 'MONGO_URI', None)

    def _discover_jobs(self, filter_tenant_id=None):
        """
        Return [(tenant_id, latest_db_name, mongo_uri)] for each active tenant.
        Falls back to the system MongoDB / single-tenant when multi-tenancy is off.
        """
        jobs = []
        multi = getattr(settings, 'MULTI_TENANCY_ENABLED', False)

        if multi:
            try:
                from core.utils.supabase_tenant import SupabaseTenant
                page, page_size = 1, 100
                while True:
                    tenants, total = SupabaseTenant.list_all(
                        active_only=True, page=page, page_size=page_size
                    )
                    for tenant in tenants:
                        if filter_tenant_id and str(tenant.id) != filter_tenant_id:
                            continue
                        if not tenant.mongo_uri or not tenant.mongo_db_prefix:
                            self.stdout.write(self.style.WARNING(
                                f"  Skipping tenant {tenant.id} — "
                                "mongo_uri or mongo_db_prefix not configured"
                            ))
                            continue
                        db_name = self._latest_db(tenant.mongo_uri, tenant.mongo_db_prefix)
                        if db_name:
                            jobs.append((str(tenant.id), db_name, tenant.mongo_uri))
                        else:
                            self.stdout.write(self.style.WARNING(
                                f"  Skipping tenant {tenant.id} — no snapshots found "
                                f"(prefix={tenant.mongo_db_prefix})"
                            ))
                    if page * page_size >= total:
                        break
                    page += 1
            except Exception as exc:
                self.stderr.write(self.style.ERROR(f"Failed to list tenants from Supabase: {exc}"))
        else:
            # Single-tenant mode: use system mongo_uri and MONGO_DB_NAME prefix
            mongo_uri = getattr(settings, 'MONGO_URI', None)
            prefix = getattr(settings, 'MONGO_DB_NAME', 'bridgesec')
            if not mongo_uri:
                self.stderr.write(self.style.ERROR("MONGO_URI is not configured."))
                return []
            db_name = self._latest_db(mongo_uri, prefix)
            if db_name:
                jobs.append((None, db_name, mongo_uri))
            else:
                self.stdout.write(self.style.WARNING(
                    f"No snapshots found with prefix={prefix}"
                ))

        return jobs

    def _latest_db(self, mongo_uri, prefix):
        """Return the name of the most recent snapshot DB for the given prefix, or None."""
        try:
            client = MongoClient(mongo_uri, serverSelectionTimeoutMS=8000)
            prefix_str = f"{prefix}_"
            candidates = sorted(
                [db for db in client.list_database_names() if db.startswith(prefix_str)],
                reverse=True,
            )
            client.close()
            return candidates[0] if candidates else None
        except Exception as exc:
            logger.warning(f"Could not list databases for prefix {prefix}: {exc}")
            return None

    def _sync_one(self, tenant_id, db_name, mongo_uri, dry_run):
        """
        Core sync logic — mirrors supabase_sync_tasks.sync_okta_users_to_supabase
        but runs inline so output is visible in the terminal.
        """
        if not mongo_uri:
            return {"status": "error", "reason": "no_mongo_uri"}

        # Read okta_user documents
        mongo_client = None
        try:
            mongo_client = MongoClient(mongo_uri, serverSelectionTimeoutMS=10000)
            db = mongo_client[db_name]

            if "okta_user" not in db.list_collection_names():
                return {"status": "skipped", "reason": "no_okta_user_collection"}

            okta_docs = list(db["okta_user"].find(
                {"email": {"$exists": True, "$nin": [None, ""]}},
                {"user_id": 1, "email": 1, "login": 1, "_id": 0},
            ))
        finally:
            if mongo_client:
                mongo_client.close()

        if not okta_docs:
            return {"status": "ok", "inserted": 0, "already_present": 0, "tenant_linked": 0}

        # Deduplicate by email
        seen: set = set()
        unique_docs = []
        for doc in okta_docs:
            email = (doc.get("email") or "").strip()
            if email and email not in seen:
                seen.add(email)
                unique_docs.append(doc)

        all_emails = [doc["email"].strip() for doc in unique_docs]
        total = len(all_emails)

        if dry_run:
            self.stdout.write(f"    [DRY RUN] {total} Okta users found in snapshot")
            return {"status": "ok", "inserted": 0, "already_present": total, "tenant_linked": 0}

        # Find existing emails in Supabase
        from core.utils.supabase_client import get_supabase_client
        sb = get_supabase_client()
        existing_map: dict = {}

        for i in range(0, total, BATCH_SIZE):
            batch = all_emails[i:i + BATCH_SIZE]
            try:
                resp = sb.table("users").select("id, email").in_("email", batch).execute()
                for row in (resp.data or []):
                    if row.get("email") and row.get("id"):
                        existing_map[row["email"].strip()] = row["id"]
            except Exception as exc:
                logger.error(f"Email lookup batch failed: {exc}")

        # Insert only new users
        new_docs = [
            doc for doc in unique_docs
            if doc.get("email", "").strip() not in existing_map
        ]
        inserted = 0

        for i in range(0, len(new_docs), BATCH_SIZE):
            batch = new_docs[i:i + BATCH_SIZE]
            rows = [
                {
                    "email":        doc.get("email", "").strip(),
                    "username":     (doc.get("login") or doc.get("email") or "").strip(),
                    "okta_user_id": doc.get("user_id"),
                    "tenant_id":    str(tenant_id) if tenant_id else None,
                    "roles":        ["user"],
                }
                for doc in batch
            ]
            try:
                resp = sb.table("users").insert(rows).execute()
                inserted += len(resp.data or [])
                for row in (resp.data or []):
                    if row.get("email") and row.get("id"):
                        existing_map[row["email"].strip()] = row["id"]
            except Exception as exc:
                logger.error(f"Insert batch (offset {i}) failed: {exc}")

        already_present = total - len(new_docs)

        return {
            "status":          "ok",
            "inserted":        inserted,
            "already_present": already_present,
        }
