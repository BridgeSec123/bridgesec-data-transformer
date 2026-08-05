"""
Backend-agnostic log reading.

get_log_reader(tenant_id) returns a reader for whichever backend that tenant
is configured for (see core.utils.tenant_logging_config), so /api/logs/*
views don't need to know if they're talking to Elasticsearch, Splunk, or Loki.
All readers return the same doc shape LogEntrySerializer expects.

Elasticsearch/Splunk/Loki are each ONE shared instance (settings.py) — the
tenant only determines WHICH reader is built, never its connection details.
"""
from core.utils.tenant_logging_config import get_logging_backend


def get_log_reader(tenant_id):
    backend = get_logging_backend(tenant_id)
    from django.conf import settings

    if backend == "splunk" and settings.SPLUNK_SEARCH_URL:
        from core.utils.log_readers.splunk_reader import SplunkLogReader
        return SplunkLogReader({
            "search_url": settings.SPLUNK_SEARCH_URL,
            "search_user": settings.SPLUNK_SEARCH_USER,
            "search_password": settings.SPLUNK_SEARCH_PASSWORD,
            "verify_ssl": settings.SPLUNK_VERIFY_SSL,
        })

    if backend == "loki" and settings.LOKI_URL:
        from core.utils.log_readers.loki_reader import LokiLogReader
        return LokiLogReader({
            "query_url": settings.LOKI_URL,
            "verify_ssl": settings.LOKI_VERIFY_SSL,
        })

    from core.utils.log_readers.es_reader import ElasticsearchLogReader
    return ElasticsearchLogReader()
