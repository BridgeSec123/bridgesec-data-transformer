"""
Management command to migrate users from MongoDB to Supabase.

Usage:
    python manage.py migrate_users_to_supabase

What it does:
1. Reads all User documents from MongoDB
2. Upserts each into the Supabase `users` table (keyed on email)
3. Preserves role and tenant_id for each user
4. Reports success / failure counts

Run BEFORE setting SUPABASE_URL + SUPABASE_KEY as the active backend,
or run once after to back-fill existing accounts.

Pre-requisite: create the table in Supabase SQL Editor first:

    CREATE TABLE public.users (
        id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        username    TEXT NOT NULL,
        email       TEXT NOT NULL UNIQUE,
        password    TEXT,
        role        TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('admin', 'user')),
        tenant_id   TEXT,
        created_at  TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE INDEX idx_users_email  ON public.users(email);
    CREATE INDEX idx_users_tenant ON public.users(tenant_id);
"""
import logging

from django.conf import settings
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Migrate all users from MongoDB to Supabase"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be migrated without writing to Supabase",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no data will be written"))

        # Verify Supabase is configured
        supabase_url = getattr(settings, "SUPABASE_URL", None)
        supabase_key = getattr(settings, "SUPABASE_KEY", None)
        if not supabase_url or not supabase_key:
            self.stderr.write(
                self.style.ERROR(
                    "SUPABASE_URL and SUPABASE_KEY must be set in .env before running this command."
                )
            )
            return

        # Load MongoDB users
        try:
            from core.models.user import User as MongoUser
            mongo_users = list(MongoUser.objects.all())
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to read MongoDB users: {e}"))
            raise

        if not mongo_users:
            self.stdout.write(self.style.WARNING("No users found in MongoDB. Nothing to migrate."))
            return

        self.stdout.write(f"Found {len(mongo_users)} user(s) in MongoDB.")

        # Connect to Supabase
        if not dry_run:
            try:
                from core.utils.supabase_client import get_supabase_client
                client = get_supabase_client()
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Failed to connect to Supabase: {e}"))
                raise

        success = 0
        failed = 0

        for mongo_user in mongo_users:
            email = mongo_user.email
            username = mongo_user.username or email
            role = mongo_user.role or "user"
            tenant_id = str(mongo_user.tenant_id) if getattr(mongo_user, "tenant_id", None) else None

            if dry_run:
                self.stdout.write(
                    f"  [DRY RUN] Would upsert: email={email}, username={username}, "
                    f"role={role}, tenant_id={tenant_id}"
                )
                success += 1
                continue

            try:
                result = (
                    client.table("users")
                    .upsert(
                        {
                            "email": email,
                            "username": username,
                            "role": role,
                            "tenant_id": tenant_id,
                        },
                        on_conflict="email",
                    )
                    .execute()
                )
                if result.data:
                    self.stdout.write(self.style.SUCCESS(f"  Migrated: {email} (role={role})"))
                    success += 1
                else:
                    self.stderr.write(self.style.ERROR(f"  No data returned for: {email}"))
                    failed += 1
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"  Failed to migrate {email}: {e}"))
                failed += 1

        self.stdout.write("")
        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"Dry run complete. Would migrate {success} user(s)."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Migration complete. Success: {success}, Failed: {failed}"))
            if failed:
                self.stdout.write(
                    self.style.WARNING(
                        "Some users failed to migrate. Check errors above and re-run the command — "
                        "upsert is safe to run multiple times."
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        "\nAll users migrated. You can now set SUPABASE_URL + SUPABASE_KEY in .env "
                        "to activate the Supabase backend."
                    )
                )
