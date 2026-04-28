from django.core.management.base import BaseCommand

from core.services import opa_sync


class Command(BaseCommand):
    help = "Manually resync all PolicyRule documents from MongoDB to OPA."

    def handle(self, *args, **options):
        result = opa_sync.sync_from_mongo()
        if result.get("skipped"):
            self.stdout.write(self.style.WARNING("OPA unreachable; sync skipped."))
            return
        self.stdout.write(self.style.SUCCESS(
            f"Synced: {result['synced']} | Removed orphans: {result['removed_orphans']}"
        ))
