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
        # APScheduler: opt-in fallback only. Celery Beat is the default scheduler, so
        # by default we do NOT start APScheduler here — otherwise `runserver` (which
        # sets RUN_MAIN) would start a SECOND scheduler alongside the Beat container
        # and double-enqueue run_scheduled_bulk_task every tick. Enable explicitly
        # with USE_APSCHEDULER=true in a deployment that uses APScheduler instead of Beat.
        from django.conf import settings
        in_main_process = (
            os.environ.get('RUN_MAIN') == 'true'
            or os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
        )
        if getattr(settings, 'USE_APSCHEDULER', False) and in_main_process:
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

        self._configure_mappings()

    def _configure_mappings(self):
        """Configure the Supabase-backed mapping provider on Django startup."""
        skip_commands = {"migrate", "makemigrations", "collectstatic"}
        if any(cmd in sys.argv for cmd in skip_commands):
            return
        try:
            from core.utils.mapping_provider import configure_mapping_provider
            configure_mapping_provider()
        except Exception as e:
            # Non-fatal — fallback to in-code dicts is automatic.
            logger.warning("Mapping provider configuration failed: %s", e)
