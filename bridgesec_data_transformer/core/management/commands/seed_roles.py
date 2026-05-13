"""
Seed the 8 system roles into Supabase.

Usage:
    python manage.py seed_roles

Safe to run multiple times — uses upsert on the `name` unique key.
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Seed system roles into the Supabase roles table."

    def handle(self, *args, **options):
        from core.utils.supabase_role import SupabaseRole, SYSTEM_ROLES
        SupabaseRole.seed_system_roles()
        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(SYSTEM_ROLES)} system roles into Supabase."
        ))
