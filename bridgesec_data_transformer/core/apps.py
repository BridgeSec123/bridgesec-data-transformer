from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        """
        Start APScheduler when Django app is ready.
        """
        import os
        # Only start scheduler in the main process, not in worker processes
        if os.environ.get('RUN_MAIN') == 'true' or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
            from core.scheduler import start_scheduler
            start_scheduler()
