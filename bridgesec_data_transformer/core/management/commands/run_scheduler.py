import logging
from django.conf import settings
from django.core.management.base import BaseCommand
from core.scheduler import start_scheduler

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Run APScheduler for bulk entity tasks (fallback scheduler; opt-in via USE_APSCHEDULER=true)'

    def handle(self, *args, **options):
        # Guard: APScheduler is the opt-in fallback. Refuse to start unless
        # USE_APSCHEDULER=true so it can't accidentally run alongside Celery Beat
        # and double-enqueue run_scheduled_bulk_task.
        if not getattr(settings, 'USE_APSCHEDULER', False):
            self.stderr.write(self.style.WARNING(
                'APScheduler not started — USE_APSCHEDULER is not enabled. '
                'Celery Beat is the default scheduler. Set USE_APSCHEDULER=true to '
                'run APScheduler instead (do NOT run both).'
            ))
            return

        self.stdout.write(self.style.SUCCESS('Starting APScheduler...'))
        start_scheduler()

        # Keep the process running
        try:
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('Scheduler stopped.'))
