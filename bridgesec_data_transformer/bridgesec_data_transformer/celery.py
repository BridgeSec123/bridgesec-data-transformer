# bridgesec_data_transformer/celery_app.py
from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
import logging.config
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bridgesec_data_transformer.settings")

app = Celery("bridgesec_data_transformer")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
logging.config.dictConfig(settings.LOGGING)
