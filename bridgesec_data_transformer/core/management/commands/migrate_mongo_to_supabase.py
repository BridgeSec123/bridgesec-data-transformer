"""
One-time migration of application data from MongoDB to Supabase.

Migrates:
  1. users         (bridgesec.users)          → public.users
  2. tenants       (bridgesec.tenants)         → public.tenants
  3. activity_logs (bridgesec.activity_logs)   → public.activity_logs
  4. policy_rules  (bridgesec.opa_policy_rules)→ public.policy_rules

Usage:
    python manage.py migrate_mongo_to_supabase [--collection <name>]

All inserts are upserts — safe to run multiple times.
"""
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Migrate MongoDB app data to Supabase (one-time, idempotent)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--collection",
            choices=["users", "tenants", "activity_logs", "policy_rules", "all"],
            default="all",
            help="Which collection to migrate (default: all)",
        )

    def handle(self, *args, **options):
        collection = options["collection"]
        try:
            from django.conf import settings
            import mongoengine

            mongo_uri = settings.MONGO_URI
            db_name   = getattr(settings, "MASTER_DB_NAME", "bridgesec_master")
            mongoengine.connect(db=db_name, host=mongo_uri, alias="migration")
            self.stdout.write(f"Connected to MongoDB: {db_name}")
        except Exception as e:
            raise CommandError(f"Cannot connect to MongoDB: {e}")

        if collection in ("users", "all"):
            self._migrate_users()
        if collection in ("tenants", "all"):
            self._migrate_tenants()
        if collection in ("activity_logs", "all"):
            self._migrate_activity_logs()
        if collection in ("policy_rules", "all"):
            self._migrate_policy_rules()

        self.stdout.write(self.style.SUCCESS("Migration complete."))

    def _migrate_users(self):
        self.stdout.write("Migrating users...")
        from pymongo import MongoClient
        from django.conf import settings
        from core.utils.supabase_client import get_supabase_client

        client = MongoClient(settings.MONGO_URI)
        db     = client[getattr(settings, "MASTER_DB_NAME", "bridgesec_master")]
        rows   = list(db["users"].find({}))
        sb     = get_supabase_client()
        count  = 0
        for row in rows:
            old_role = row.get("role", "user")
            roles = ["tenant_admin"] if old_role == "admin" else ["user"]
            data = {
                "email":     row.get("email"),
                "username":  row.get("username") or row.get("email"),
                "roles":     roles,
                "tenant_id": str(row["tenant_id"]) if row.get("tenant_id") else None,
            }
            if not data["email"]:
                continue
            sb.table("users").upsert(data, on_conflict="email").execute()
            count += 1
        self.stdout.write(self.style.SUCCESS(f"  users: {count} migrated"))

    def _migrate_tenants(self):
        self.stdout.write("Migrating tenants...")
        from pymongo import MongoClient
        from django.conf import settings
        from core.utils.supabase_client import get_supabase_client

        client = MongoClient(settings.MONGO_URI)
        db     = client[getattr(settings, "MASTER_DB_NAME", "bridgesec_master")]
        rows   = list(db["tenants"].find({}))
        sb     = get_supabase_client()
        count  = 0
        for row in rows:
            data = {
                "name":                 row.get("name"),
                "okta_domain":          row.get("okta_domain"),
                "okta_client_id":       row.get("okta_client_id"),
                "okta_client_secret":   row.get("okta_client_secret"),
                "okta_issuer":          row.get("okta_issuer"),
                "mongo_uri":            row.get("mongo_uri"),
                "mongo_db_prefix":      row.get("mongo_db_prefix"),
                "terraform_server_url": row.get("terraform_server_url"),
                "terraform_state_path": row.get("terraform_state_path"),
                "service_client_id":    row.get("service_client_id"),
                "service_private_key":  row.get("service_private_key"),
                "service_scopes":       row.get("service_scopes"),
                "is_active":            row.get("is_active", True),
            }
            if not data["name"] or not data["okta_domain"]:
                continue
            sb.table("tenants").upsert(data, on_conflict="name").execute()
            count += 1
        self.stdout.write(self.style.SUCCESS(f"  tenants: {count} migrated"))

    def _migrate_activity_logs(self):
        self.stdout.write("Migrating activity logs (last 30 days)...")
        from pymongo import MongoClient
        from datetime import datetime, timedelta
        from django.conf import settings
        from core.utils.supabase_client import get_supabase_client

        client    = MongoClient(settings.MONGO_URI)
        db        = client[getattr(settings, "MASTER_DB_NAME", "bridgesec_master")]
        cutoff    = datetime.utcnow() - timedelta(days=30)
        rows      = list(db["activity_logs"].find({"timestamp": {"$gte": cutoff}}))
        sb        = get_supabase_client()
        count     = 0
        batch     = []
        for row in rows:
            batch.append({
                "user_email":  row.get("user_email") or "unknown",
                "action":      row.get("action") or "unknown",
                "tenant_id":   str(row["tenant_id"]) if row.get("tenant_id") else None,
                "entity_name": row.get("entity_name"),
                "db_name":     row.get("db_name"),
                "status":      row.get("status", "success"),
                "ip_address":  row.get("ip_address"),
                "details":     row.get("details") or {},
                "timestamp":   row["timestamp"].isoformat() if row.get("timestamp") else None,
            })
            if len(batch) >= 100:
                sb.table("activity_logs").insert(batch).execute()
                count += len(batch)
                batch = []
        if batch:
            sb.table("activity_logs").insert(batch).execute()
            count += len(batch)
        self.stdout.write(self.style.SUCCESS(f"  activity_logs: {count} migrated"))

    def _migrate_policy_rules(self):
        self.stdout.write("Migrating policy rules...")
        from pymongo import MongoClient
        from django.conf import settings
        from core.utils.supabase_client import get_supabase_client

        client = MongoClient(settings.MONGO_URI)
        db     = client[getattr(settings, "MASTER_DB_NAME", "bridgesec_master")]
        rows   = list(db["opa_policy_rules"].find({}))
        sb     = get_supabase_client()
        count  = 0
        for row in rows:
            policy_id = str(row.get("_id") or row.get("policy_id") or "")
            if not policy_id:
                continue
            data = {
                "id":          policy_id,
                "name":        row.get("name", ""),
                "description": row.get("description", ""),
                "role":        row.get("role", "*"),
                "entity":      row.get("entity", "*"),
                "action":      row.get("action", "*"),
                "effect":      row.get("effect", "allow"),
                "conditions":  row.get("conditions") or {},
                "rego_source": row.get("rego_source"),
                "created_by":  row.get("created_by"),
            }
            sb.table("policy_rules").upsert(data, on_conflict="id").execute()
            count += 1
        self.stdout.write(self.style.SUCCESS(f"  policy_rules: {count} migrated"))
