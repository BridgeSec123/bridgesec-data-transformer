"""
Log streaming service — ES polling logic.

This service is transport-agnostic. It yields dicts that can be formatted as:
- SSE (Phase 1)
- WebSocket messages (Phase 3)
- Celery task updates (Phase 2)

No Django dependencies — unit testable.
"""

import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Iterator, Optional

from core.utils.es_client import get_es_client, ConnectionError as ESConnectionError, RequestError as ESRequestError
from core.utils.es_query_builder import build_live_log_query, INDEX_PATTERN
from core.serializers.log_serializer import LogEntrySerializer


def hit_to_dict(hit: dict) -> dict:
    """Flatten an ES search hit into the shape LogEntrySerializer expects."""
    doc = hit.get("_source", {})
    doc["_id"] = hit.get("_id")
    # Normalise both timestamp field names Filebeat may produce
    if "@timestamp" in doc and "timestamp" not in doc:
        doc["timestamp"] = doc["@timestamp"]
    return doc


class LogStreamService:
    """
    Reusable service for polling Elasticsearch and yielding log entries.

    Design goals:
    - Testable: no Django dependencies, can be unit tested with mocked ES client
    - Scalable: works with sync views, async views, Celery tasks
    - Migrateable: works now with sync generators, can become async later

    Example usage:
        service = LogStreamService()
        for event in service.poll_logs(filters={'component': 'celery'}):
            if event['type'] == 'log':
                print(event['data'])
    """

    def __init__(
        self,
        poll_interval: int = 2,
        heartbeat_interval: int = 15,
        initial_lookback_seconds: int = 30,
        tenant_id: Optional[str] = None,
    ):
        """
        Initialize the streaming service.

        Args:
            poll_interval: Seconds between ES queries (default: 2)
            heartbeat_interval: Seconds between keep-alive pings (default: 15)
            initial_lookback_seconds: How far back to start (default: 30)
            tenant_id: Scope stream to this tenant's logs only
        """
        self.poll_interval = poll_interval
        self.heartbeat_interval = heartbeat_interval
        self.initial_lookback_seconds = initial_lookback_seconds
        self.tenant_id = tenant_id
        self.es_client = get_es_client()

    def get_initial_timestamp(self) -> str:
        """
        Compute the timestamp cursor for a new stream.

        Returns ISO-8601 string of (now - lookback_seconds).
        Format: "2026-04-07T10:00:00.123Z"

        This ensures new clients see recent context, not all logs since day 1.
        """
        initial_ts = (
            datetime.now(tz=timezone.utc) - timedelta(seconds=self.initial_lookback_seconds)
        )
        # Format: "2026-04-07T10:00:00.123Z"
        return initial_ts.strftime("%Y-%m-%dT%H:%M:%S.") + \
               f"{initial_ts.microsecond // 1000:03d}Z"

    def poll_logs(self) -> Iterator[Dict]:
        """
        Continuously poll ES for new logs and yield events.

        This is a generator that runs indefinitely until the client disconnects.

        Yields:
            Dict with structure:
            - {"type": "log", "data": {...}}       ← A log entry (from ES)
            - {"type": "heartbeat"}                ← Keep-alive ping (no data)
            - {"type": "error", "error": str, "detail": str}  ← Error event

        The transport layer (SSE, WebSocket) is responsible for formatting these dicts.

        Example:
            for event in service.poll_logs():
                if event['type'] == 'log':
                    print(f"Got log: {event['data']}")
                elif event['type'] == 'error':
                    print(f"Error: {event['detail']}")
        """
        # Initialize cursor to 30 seconds ago
        last_ts = self.get_initial_timestamp()
        last_heartbeat = time.monotonic()

        # Poll indefinitely
        while True:
            try:
                # Build ES query for logs newer than last_ts, scoped to this tenant
                body = build_live_log_query(last_timestamp=last_ts, tenant_id=self.tenant_id)
                result = self.es_client.search(index=INDEX_PATTERN, body=body)
                hits = result["hits"]["hits"]

                # Yield each log entry
                if hits:
                    for hit in hits:
                        last_heartbeat = time.monotonic()
                        doc = hit_to_dict(hit)
                        serialized = LogEntrySerializer(doc).data
                        yield {"type": "log", "data": serialized}

                    # Advance cursor to the latest timestamp seen
                    # Next query will only return logs AFTER this timestamp
                    last_ts = hits[-1]["_source"]["@timestamp"]

            except ESConnectionError as exc:
                # Elasticsearch is unavailable
                yield {
                    "type": "error",
                    "error": "ES_CONNECTION_ERROR",
                    "detail": str(exc),
                }
                last_heartbeat = time.monotonic()

            except ESRequestError as exc:
                # Query is invalid (e.g., bad filter)
                yield {
                    "type": "error",
                    "error": "ES_REQUEST_ERROR",
                    "detail": str(exc),
                }
                last_heartbeat = time.monotonic()

            except Exception as exc:
                # Unexpected error
                yield {
                    "type": "error",
                    "error": "INTERNAL_ERROR",
                    "detail": "Unexpected error polling logs",
                }
                last_heartbeat = time.monotonic()

            # Heartbeat: send keep-alive every 15 seconds of silence
            # This keeps TCP alive and prevents proxy/firewall timeouts
            if time.monotonic() - last_heartbeat >= self.heartbeat_interval:
                last_heartbeat = time.monotonic()
                yield {"type": "heartbeat"}

            # Sleep before next poll
            time.sleep(self.poll_interval)
