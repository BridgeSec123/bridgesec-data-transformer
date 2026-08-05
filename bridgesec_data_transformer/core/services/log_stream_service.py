"""
Log streaming service — polls whichever backend the tenant is configured
for (Elasticsearch/Splunk/Loki, via LogReader.tail()) and yields events.

This service is transport-agnostic. It yields dicts that can be formatted as:
- SSE (Phase 1)
- WebSocket messages (Phase 3)
- Celery task updates (Phase 2)
"""

import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Iterator, Optional

from core.utils.log_readers import get_log_reader
from core.serializers.log_serializer import LogEntrySerializer


class LogStreamService:
    """
    Reusable service for polling the tenant's log backend and yielding log entries.

    Example usage:
        service = LogStreamService(tenant_id="...")
        for event in service.poll_logs():
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
            poll_interval: Seconds between backend queries (default: 2)
            heartbeat_interval: Seconds between keep-alive pings (default: 15)
            initial_lookback_seconds: How far back to start (default: 30)
            tenant_id: Scope stream to this tenant's logs only
        """
        self.poll_interval = poll_interval
        self.heartbeat_interval = heartbeat_interval
        self.initial_lookback_seconds = initial_lookback_seconds
        self.tenant_id = tenant_id
        self.reader = get_log_reader(tenant_id)

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
                # Fetch logs newer than last_ts, scoped to this tenant, from
                # whichever backend this tenant is configured for.
                docs = self.reader.tail(self.tenant_id, last_timestamp=last_ts)

                # Yield each log entry
                if docs:
                    for doc in docs:
                        last_heartbeat = time.monotonic()
                        serialized = LogEntrySerializer(doc).data
                        yield {"type": "log", "data": serialized}

                    # Advance cursor to the latest timestamp seen
                    # Next query will only return logs AFTER this timestamp
                    last_ts = docs[-1].get("@timestamp") or docs[-1].get("timestamp") or last_ts

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
