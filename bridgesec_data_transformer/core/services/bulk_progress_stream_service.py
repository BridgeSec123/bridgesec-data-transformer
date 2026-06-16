"""
Service that polls the `bulk_progress` MongoDB collection and yields
structured events for the SSE progress stream.

Yields dicts:
  {"type": "progress",   "data": <job_doc_with_progress_pct>}
  {"type": "complete",   "data": <job_doc_with_progress_pct>}
  {"type": "heartbeat"}
  {"type": "error",      "error": <message>}

The generator terminates after yielding the "complete" (or "error") event.
"""
import time

from core.utils.progress_store import get_bulk_job


class BulkProgressStreamService:
    POLL_INTERVAL = 2        # seconds between MongoDB polls
    HEARTBEAT_INTERVAL = 15  # seconds of silence before sending a heartbeat
    MAX_STREAM_DURATION = 1800  # 30 min hard cutoff — handles SIGKILL / broker crash
                                # where Celery signals cannot fire

    def __init__(self, request_id: str, mongo_uri: str = None):
        self.request_id = request_id
        self.mongo_uri = mongo_uri

    def stream(self):
        """
        Generator — poll loop.  Terminates when:
          - status reaches "completed" or "failed"  (normal path)
          - job document is not found               (bad request_id)
          - MAX_STREAM_DURATION is exceeded         (worker killed / broker crash)
        """
        stream_started = time.time()
        last_heartbeat = time.time()

        while True:
            # Hard timeout — catches SIGKILL and other unrecoverable interruptions
            # where Celery signals never fire and the job doc stays stuck in "running"
            if time.time() - stream_started > self.MAX_STREAM_DURATION:
                yield {
                    "type": "error",
                    "error": "Stream timed out — bulk job may have been interrupted",
                }
                return

            job = get_bulk_job(self.request_id, mongo_uri=self.mongo_uri)

            if job is None:
                yield {"type": "error", "error": f"Job '{self.request_id}' not found"}
                return

            # Make _id JSON-serializable
            job["_id"] = str(job["_id"])

            # Compute progress percentage
            total = job.get("total") or 1
            completed = job.get("completed", 0)
            job["progress_pct"] = round(completed / total * 100)

            job_status = job.get("status")

            if job_status in ("completed", "failed"):
                yield {"type": "complete", "data": job}
                return

            yield {"type": "progress", "data": job}
            last_heartbeat = time.time()

            time.sleep(self.POLL_INTERVAL)

            # Heartbeat if silence exceeds the interval
            if time.time() - last_heartbeat >= self.HEARTBEAT_INTERVAL:
                yield {"type": "heartbeat"}
                last_heartbeat = time.time()
