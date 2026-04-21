"""
MongoDB wrapper for bulk-fetch job progress tracking.

All writes use atomic $inc / $set to stay safe under concurrent Celery workers.
The collection (`bulk_progress`) lives in settings.MONGO_DB_NAME (the control-plane
DB), NOT in the per-snapshot DB.
"""
from datetime import datetime, timezone

from django.conf import settings


def _col():
    """Return the bulk_progress collection from the control-plane DB."""
    return settings.MONGO_CLIENT[settings.MONGO_DB_NAME]["bulk_progress"]


def create_bulk_job(request_id: str, db_name: str, entity_keys: list):
    """
    Insert the initial job document.  Called once, just before the chord is dispatched.
    Uses $setOnInsert so a duplicate call never overwrites (idempotent).
    """
    entities = {key: {"status": "pending"} for key in entity_keys}
    _col().update_one(
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


def update_entity_done(request_id: str, entity_name: str, record_counts: dict, time_s: float):
    """
    Mark one entity as successfully completed with data.
    Increments both `completed` and `entities_with_data`.
    """
    total_records = sum(record_counts.values()) if record_counts else 0
    _col().update_one(
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


def mark_entity_empty(request_id: str, entity_name: str):
    """
    Mark one entity as completed but with zero records (empty Okta response).
    Only `completed` is incremented — `entities_with_data` stays the same.
    """
    _col().update_one(
        {"_id": request_id},
        {
            "$inc": {"completed": 1},
            "$set": {f"entities.{entity_name}": {"status": "empty"}},
        },
    )


def update_entity_error(request_id: str, entity_name: str, error: str):
    """
    Mark one entity as failed.  Increments both `completed` and `failed`.
    """
    _col().update_one(
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


def set_job_status(request_id: str, new_status: str):
    """Generic status setter — used for 'diff_running' and 'failed'."""
    _col().update_one(
        {"_id": request_id},
        {"$set": {"status": new_status}},
    )


def set_job_completed(request_id: str, diff_summary: dict):
    """
    Mark the job as fully completed and attach the diff summary.
    Called by the diff task after writing the _diff_report summary doc.
    """
    _col().update_one(
        {"_id": request_id},
        {
            "$set": {
                "status":       "completed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "diff_summary": diff_summary,
            }
        },
    )


def get_bulk_job(request_id: str):
    """Return the full job document, or None if not found."""
    return _col().find_one({"_id": request_id})
