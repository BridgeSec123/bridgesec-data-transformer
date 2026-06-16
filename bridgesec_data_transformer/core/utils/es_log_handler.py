"""
Non-blocking Elasticsearch logging handler.

Pushes each log record into  bridgesec-logs-YYYY.MM.DD  (matching the
INDEX_PATTERN = "bridgesec-logs-*" used by the query builder).

Uses a background thread + queue so it never blocks the main request thread.
Silently drops records when the queue is full (safety valve) rather than
crashing the application.
"""
import json
import logging
import queue
import threading
from datetime import datetime, timezone


class ElasticsearchHandler(logging.Handler):
    """
    Logging handler that ships records to Elasticsearch asynchronously.

    Records are placed on an in-process queue and consumed by a single
    daemon thread.  The thread is started lazily on the first emit() call.
    """

    MAX_QUEUE_SIZE = 2000   # drop oldest if backpressure builds
    FLUSH_TIMEOUT  = 2.0    # seconds to wait for worker on shutdown

    def __init__(self, es_url: str = "http://localhost:9200", level=logging.DEBUG):
        super().__init__(level)
        self._es_url  = es_url
        self._queue   = queue.Queue(maxsize=self.MAX_QUEUE_SIZE)
        self._started = False
        self._lock    = threading.Lock()

    # ------------------------------------------------------------------
    # logging.Handler interface
    # ------------------------------------------------------------------

    def emit(self, record: logging.LogRecord) -> None:
        try:
            doc = self._record_to_doc(record)
            self._queue.put_nowait(doc)
            self._ensure_worker()
        except queue.Full:
            pass   # drop — never block the caller
        except Exception:
            self.handleError(record)

    def close(self) -> None:
        """Flush remaining records before the process exits."""
        try:
            self._queue.join()
        except Exception:
            pass
        super().close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_worker(self) -> None:
        if self._started:
            return
        with self._lock:
            if not self._started:
                t = threading.Thread(target=self._worker, daemon=True, name="es-log-worker")
                t.start()
                self._started = True

    def _worker(self) -> None:
        """Background thread: drain the queue and index docs into ES."""
        from elasticsearch import Elasticsearch, ConnectionError as ESConnError

        es = Elasticsearch(
            self._es_url,
            retry_on_timeout=False,
            max_retries=0,
            request_timeout=15,
        )

        while True:
            try:
                doc = self._queue.get(timeout=1)
            except queue.Empty:
                continue

            try:
                index = f"bridgesec-logs-{datetime.now(timezone.utc).strftime('%Y.%m.%d')}"
                es.index(index=index, document=doc)
            except ESConnError:
                pass   # ES down — drop record, keep worker alive
            except Exception:
                pass   # unexpected error — drop silently, keep worker alive
            finally:
                self._queue.task_done()

    @staticmethod
    def _record_to_doc(record: logging.LogRecord) -> dict:
        """Convert a LogRecord into the ES document shape the query builder expects."""
        now = datetime.now(timezone.utc)

        doc = {
            "@timestamp": now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "timestamp":  now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "levelname":  record.levelname,
            "level":      record.levelname,
            "name":       record.name,
            "module":     record.module,
            "funcName":   record.funcName,
            "lineno":     record.lineno,
            "message":    record.getMessage(),
            "request_id": None,
            "component":  None,
            "entity_type": None,
            "operation":  None,
            "action":     None,
            "user":       None,
            "tenant_id":  "unknown",
        }

        # Pull structured fields injected via logger.xxx(..., extra={...}) or TenantContextFilter
        for field in ("request_id", "component", "entity_type", "operation", "action", "user", "tenant_id"):
            val = getattr(record, field, None)
            if val is not None:
                doc[field] = str(val)

        # Defense-in-depth: if TenantContextFilter didn't run (handler misconfigured or
        # called outside a request/task with set_current_tenant), try the ContextVar directly.
        if doc["tenant_id"] == "unknown":
            try:
                from core.utils.tenant_utils import get_current_tenant
                _tenant = get_current_tenant()
                if _tenant:
                    doc["tenant_id"] = str(_tenant.id)
            except Exception:
                pass

        # Exception info
        if record.exc_info:
            import traceback
            doc["exc_info"] = "".join(traceback.format_exception(*record.exc_info))

        return doc
