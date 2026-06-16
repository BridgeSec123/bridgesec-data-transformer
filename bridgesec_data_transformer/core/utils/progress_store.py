"""
MongoDB wrapper for bulk-fetch job progress tracking.

All writes use atomic $inc / $set to stay safe under concurrent Celery workers.

In single-tenant mode (no mongo_uri supplied) the collection lives in the
control-plane DB resolved by get_system_mongo_client().

In multi-tenant mode every caller passes the tenant's mongo_uri so the
progress doc lives in the SAME cluster as the fetched Okta data.  This
ensures the web process (create + read) and the Celery workers (updates)
always hit the same physical MongoDB, regardless of Postgres row ordering.
"""
from datetime import datetime, timezone

from django.conf import settings


def _col(mongo_uri=None):
    """Return the bulk_progress collection.

    When mongo_uri is provided, open (or reuse) a client for that URI so the
    progress doc lives in the tenant's own cluster.  Otherwise fall back to the
    system-level client (single-tenant / scheduled-run path).
    """
    from django.conf import settings as _s
    if mongo_uri:
        from core.utils.tenant_utils import get_client_for_uri
        client = get_client_for_uri(mongo_uri)
    else:
        from core.utils.mongo_utils import get_system_mongo_client
        client = get_system_mongo_client()
    return client[_s.MONGO_DB_NAME]["bulk_progress"]


def create_bulk_job(request_id: str, db_name: str, entity_keys: list, mongo_uri: str = None):
    """
    Insert the initial job document.  Called once, just before the chord is dispatched.
    Uses $setOnInsert so a duplicate call never overwrites (idempotent).
    """
    entities = {key: {"status": "pending"} for key in entity_keys}
    _col(mongo_uri).update_one(
        {"_id": request_id},
        {
            "$setOnInsert": {
                "_id":                request_id,
                "request_id":         request_id,
                "db_name":            db_name,
                "total":              len(entity_keys),
                "completed":          0,
                "failed":             0,
                "entities_with_data": 0,
                "status":             "running",
                "started_at":         datetime.now(timezone.utc).isoformat(),
                "completed_at":       None,
                "diff_summary":       None,
                "entities":           entities,
            }
        },
        upsert=True,
    )


def mark_entity_running(request_id: str, entity_name: str, worker_id: str = None, mongo_uri: str = None):
    """
    Mark one entity as actively being processed by a Celery worker.
    Called at the very start of process_single_entity_group so the SSE stream
    reflects up to 4 concurrent 'running' entities at any given time.
    """
    _col(mongo_uri).update_one(
        {"_id": request_id},
        {
            "$set": {
                f"entities.{entity_name}": {
                    "status":     "running",
                    "worker_id":  worker_id,
                    "started_at": datetime.now(timezone.utc).isoformat(),
                }
            }
        },
    )


def update_entity_done(request_id: str, entity_name: str, record_counts: dict, time_s: float, mongo_uri: str = None):
    """
    Mark one entity as successfully completed with data.
    Increments both `completed` and `entities_with_data`.
    """
    total_records = sum(record_counts.values()) if record_counts else 0
    _col(mongo_uri).update_one(
        {"_id": request_id},
        {
            "$inc": {"completed": 1, "entities_with_data": 1},
            "$set": {
                f"entities.{entity_name}": {
                    "status":                  "success",
                    "total_records":           total_records,
                    "record_counts":           record_counts,
                    "processing_time_seconds": round(time_s, 2),
                }
            },
        },
    )


def mark_entity_empty(request_id: str, entity_name: str, mongo_uri: str = None):
    """
    Mark one entity as completed but with zero records (empty Okta response).
    Only `completed` is incremented — `entities_with_data` stays the same.
    """
    _col(mongo_uri).update_one(
        {"_id": request_id},
        {
            "$inc": {"completed": 1},
            "$set": {f"entities.{entity_name}": {"status": "empty"}},
        },
    )


def update_entity_error(request_id: str, entity_name: str, error: str, mongo_uri: str = None):
    """
    Mark one entity as failed.  Increments both `completed` and `failed`.
    """
    _col(mongo_uri).update_one(
        {"_id": request_id},
        {
            "$inc": {"completed": 1, "failed": 1},
            "$set": {
                f"entities.{entity_name}": {
                    "status": "error",
                    "error":  error,
                }
            },
        },
    )


def set_job_status(request_id: str, new_status: str, mongo_uri: str = None):
    """Generic status setter — used for 'diff_running' and 'failed'."""
    _col(mongo_uri).update_one(
        {"_id": request_id},
        {"$set": {"status": new_status}},
    )


def set_job_completed(request_id: str, diff_summary: dict, mongo_uri: str = None):
    """
    Mark the job as fully completed and attach the diff summary.
    Called by the diff task after writing the _diff_report summary doc.
    """
    _col(mongo_uri).update_one(
        {"_id": request_id},
        {
            "$set": {
                "status":       "completed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "diff_summary": diff_summary,
            }
        },
    )


def get_bulk_job(request_id: str, mongo_uri: str = None):
    """Return the full job document, or None if not found."""
    return _col(mongo_uri).find_one({"_id": request_id})
