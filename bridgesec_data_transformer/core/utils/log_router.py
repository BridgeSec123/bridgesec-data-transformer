"""
TenantLogRouter — dispatches each log record to the destination configured
for its tenant (elasticsearch | splunk | loki), instead of every tenant's
logs going to one hardcoded handler.

Elasticsearch/Splunk/Loki are each ONE shared instance (settings.py), so a
handler is built once per backend (at most 3 total) and reused for every
tenant on that backend — not once per tenant.
"""
import logging

from core.utils.tenant_logging_config import get_logging_backend

logger = logging.getLogger(__name__)


class TenantLogRouter(logging.Handler):
    def __init__(self, level=logging.DEBUG):
        super().__init__(level)
        self._handlers = {}  # backend name -> logging.Handler instance
        self._warned_tenants = set()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            tenant_id = getattr(record, "tenant_id", None)
            backend = get_logging_backend(tenant_id if tenant_id != "unknown" else None)
            handler = self._get_handler(backend, tenant_id)
            handler.emit(record)
        except Exception:
            self.handleError(record)

    def _get_handler(self, backend, tenant_id):
        handler = self._handlers.get(backend)
        if handler is not None:
            return handler

        handler = self._build_handler(backend, tenant_id)
        self._handlers[backend] = handler
        return handler

    def _build_handler(self, backend, tenant_id):
        from django.conf import settings
        try:
            if backend == "splunk":
                from core.utils.splunk_log_handler import SplunkHandler
                if not settings.SPLUNK_HEC_URL or not settings.SPLUNK_HEC_TOKEN:
                    raise ValueError("SPLUNK_HEC_URL/SPLUNK_HEC_TOKEN not configured")
                return SplunkHandler(hec_url=settings.SPLUNK_HEC_URL, hec_token=settings.SPLUNK_HEC_TOKEN)

            if backend == "loki":
                from logging_loki import LokiHandler
                if not settings.LOKI_URL:
                    raise ValueError("LOKI_URL not configured")
                return LokiHandler(
                    url=f"{settings.LOKI_URL}/loki/api/v1/push",
                    tags={"app": "bridgesec"},
                    version="1",
                )

            if backend == "elasticsearch":
                return self._elasticsearch_handler()

            raise ValueError(f"unknown logging_backend: {backend!r}")
        except Exception as e:
            if tenant_id not in self._warned_tenants:
                self._warned_tenants.add(tenant_id)
                logger.warning(
                    f"Falling back to elasticsearch for tenant_id={tenant_id}: "
                    f"logging_backend={backend!r} unavailable ({e})"
                )
            return self._elasticsearch_handler()

    def _elasticsearch_handler(self):
        handler = self._handlers.get("elasticsearch")
        if handler is None:
            from django.conf import settings
            from core.utils.es_log_handler import ElasticsearchHandler
            handler = ElasticsearchHandler(es_url=settings.ELASTICSEARCH_URL)
            self._handlers["elasticsearch"] = handler
        return handler
