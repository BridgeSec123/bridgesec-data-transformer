"""
Non-blocking Splunk (HEC) logging handler.

Same shape as core.utils.es_log_handler.ElasticsearchHandler: a background
thread + queue so it never blocks the caller, drops records on backpressure
rather than crashing the application.
"""
import logging
import queue
import threading
from datetime import datetime, timezone

from core.utils.es_log_handler import ElasticsearchHandler


class SplunkHandler(logging.Handler):
    """
    Logging handler that ships records to Splunk's HTTP Event Collector (HEC)
    asynchronously. Requires hec_url (e.g. https://splunk:8088) and hec_token.
    """

    MAX_QUEUE_SIZE = 2000

    def __init__(self, hec_url: str, hec_token: str, level=logging.DEBUG):
        super().__init__(level)
        self._hec_url = hec_url.rstrip("/")
        self._hec_token = hec_token
        self._queue = queue.Queue(maxsize=self.MAX_QUEUE_SIZE)
        self._started = False
        self._lock = threading.Lock()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            doc = ElasticsearchHandler._record_to_doc(record)
            self._queue.put_nowait(doc)
            self._ensure_worker()
        except queue.Full:
            pass
        except Exception:
            self.handleError(record)

    def close(self) -> None:
        try:
            self._queue.join()
        except Exception:
            pass
        super().close()

    def _ensure_worker(self) -> None:
        if self._started:
            return
        with self._lock:
            if not self._started:
                t = threading.Thread(target=self._worker, daemon=True, name="splunk-log-worker")
                t.start()
                self._started = True

    def _worker(self) -> None:
        import requests

        headers = {"Authorization": f"Splunk {self._hec_token}"}
        collector_url = f"{self._hec_url}/services/collector/event"

        while True:
            try:
                doc = self._queue.get(timeout=1)
            except queue.Empty:
                continue

            try:
                payload = {
                    "time": datetime.now(timezone.utc).timestamp(),
                    # "_json" sourcetype makes Splunk auto-extract top-level
                    # JSON keys (tenant_id, user_email, ...) as searchable
                    # fields at index time, matching what splunk_reader.py expects.
                    "sourcetype": "_json",
                    "index": "bridgesec_logs",
                    "event": doc,
                }
                requests.post(collector_url, json=payload, headers=headers, timeout=5)
            except Exception:
                pass  # Splunk down/unreachable — drop record, keep worker alive
            finally:
                self._queue.task_done()
