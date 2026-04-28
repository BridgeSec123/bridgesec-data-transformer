import logging
import os
import sys

from django.apps import AppConfig


logger = logging.getLogger(__name__)


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        """
        Startup hook — runs once when Django finishes loading apps.
        """
        # APScheduler: only start in the main process, not in reload/worker processes
        if os.environ.get('RUN_MAIN') == 'true' or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
            from core.scheduler import start_scheduler
            start_scheduler()

        self._sync_opa_policies()

    def _sync_opa_policies(self):
        """Re-push all policies from MongoDB to OPA on Django startup."""
        # Skip during migrations / makemigrations / test collection / shell
        skip_commands = {"migrate", "makemigrations", "collectstatic", "test"}
        if any(cmd in sys.argv for cmd in skip_commands):
            return
        if os.environ.get("SKIP_OPA_SYNC") == "true":
            return

        from django.conf import settings
        if not getattr(settings, "OPA_ENABLED", True):
            return

        try:
            from core.services import opa_sync
            result = opa_sync.sync_from_mongo()
            logger.info(
                "OPA startup sync: synced=%d removed_orphans=%d",
                result.get("synced", 0),
                result.get("removed_orphans", 0),
            )
        except Exception as e:
            # Non-fatal — the app still starts; resync endpoint / CLI can fix it later.
            logger.warning("OPA startup sync failed: %s", e)
