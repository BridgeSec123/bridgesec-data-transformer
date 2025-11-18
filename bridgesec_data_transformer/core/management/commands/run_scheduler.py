import logging
from django.core.management.base import BaseCommand
from core.scheduler import start_scheduler

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Run APScheduler for bulk entity tasks'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting APScheduler...'))
        start_scheduler()

        # Keep the process running
        try:
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('Scheduler stopped.'))
