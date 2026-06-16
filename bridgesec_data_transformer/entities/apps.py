from django.apps import AppConfig


class EntitiesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'entities'

    def ready(self):
        """
        Create MongoDB indexes for pending_deletion_plans on startup.

        TTL index (expireAfterSeconds=900): auto-expires plan documents after 15 min.
        Unique index on plan_id: prevents accidental duplicate inserts.

        create_index() is idempotent — safe to call on every startup.
        """
        from django.conf import settings
        try:
            from core.utils.mongo_utils import get_system_mongo_client
            col = get_system_mongo_client()[settings.MONGO_DB_NAME]["pending_deletion_plans"]
            col.create_index("created_at", expireAfterSeconds=900, background=True)
            col.create_index("plan_id", unique=True, background=True)
        except Exception:
            # Non-fatal: indexes may already exist or MongoDB may not be reachable yet.
            pass
