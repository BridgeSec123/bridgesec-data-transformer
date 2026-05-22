"""
Seed the entity_catalog Supabase table from FULL_ENTITY_REGISTRY.

Usage:
    python manage.py seed_entity_catalog           # upsert — skips existing rows
    python manage.py seed_entity_catalog --force   # delete all and recreate

Safe to re-run. Covers all 36 entity groups including those currently
inactive (commented out of ENTITY_VIEWSETS).
"""
import json
from django.core.management.base import BaseCommand
from entities.registry import FULL_ENTITY_REGISTRY


class Command(BaseCommand):
    help = "Seed entity_catalog in Supabase from FULL_ENTITY_REGISTRY."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Delete all existing rows and recreate from scratch.",
        )

    def handle(self, *args, **options):
        from core.utils.supabase_client import get_supabase_client
        sb = get_supabase_client()

        if options["force"]:
            sb.table("entity_catalog").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
            self.stdout.write("Deleted all existing entity_catalog rows.")

        created = updated = skipped = 0

        for name, meta in FULL_ENTITY_REGISTRY.items():
            row = {
                "name":         name,
                "display_name": meta["display_name"],
                "category":     meta["category"],
                "description":  meta.get("description", ""),
                "collections":  json.dumps(meta.get("collections", [])),
                "is_active":    meta["is_active"],
            }

            existing = (
                sb.table("entity_catalog")
                .select("id, is_active")
                .eq("name", name)
                .limit(1)
                .execute()
            )

            if existing.data:
                if options["force"]:
                    sb.table("entity_catalog").update(row).eq("name", name).execute()
                    updated += 1
                    self.stdout.write(f"  updated : {name}")
                else:
                    skipped += 1
            else:
                sb.table("entity_catalog").insert(row).execute()
                created += 1
                self.stdout.write(f"  created : {name}  (active={meta['is_active']})")

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone — {created} created, {updated} updated, {skipped} skipped."
            )
        )
