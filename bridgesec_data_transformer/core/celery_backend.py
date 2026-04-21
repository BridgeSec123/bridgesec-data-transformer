"""
Custom Celery result backend: MongoDB with mongodb+srv:// (Atlas SRV) support.

Celery's stock MongoBackend prepends "mongodb://" to any host string that
doesn't already start with that exact prefix — it does not recognise
"mongodb+srv://". The result is a double-prefixed, malformed URI that
pymongo then mis-parses (treating credentials/hostname as the database
name), producing: InvalidURI: Bad database name "/user:pass@cluster...".

This subclass overrides _get_connection() to bypass that logic and pass
settings.MONGO_URI directly to pymongo, which handles SRV URIs natively
via dnspython (already listed in requirements.txt).
"""

from celery.backends.mongodb import MongoBackend
from django.conf import settings
from pymongo import MongoClient


class MongoSRVBackend(MongoBackend):
    def _get_connection(self):
        if not getattr(self, '_connection', None):
            self._connection = MongoClient(
                settings.MONGO_URI,
                serverSelectionTimeoutMS=10000,
            )
        return self._connection
