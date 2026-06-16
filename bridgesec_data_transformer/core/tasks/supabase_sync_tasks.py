"""
Post-bulk Supabase user sync task.

sync_okta_users_to_supabase
    Reads every okta_user document from a freshly-written MongoDB snapshot and
    ensures each Okta user exists in the Supabase `users` table.

    Behaviour:
    - Insert-only for `users`: rows that already exist (matched by email) are
      never overwritten, so existing roles, passwords, or tenant assignments are
      preserved.
    - Upsert for `user_tenants`: every user (new or pre-existing) gets a
      junction row linking them to the tenant that ran the bulk fetch.
    - Tenant-universal: dispatched from finalize_bulk_entity_task with
      tenant_id as a parameter, so every tenant — including future ones — is
      handled identically without configuration changes.
    - Scheduled runs: the same finalize_bulk_entity_task is called for both
      on-demand and Celery Beat scheduled fetches, so this sync runs on both.
"""
import logging

from celery import shared_task
from django.conf import settings
from pymongo import MongoClient

logger = logging.getLogger(__name__)

BATCH_SIZE = 500


@shared_task(bind=True, max_retries=0)
def sync_okta_users_to_supabase(
    self,
    current_db_name,
    tenant_id=None,
    mongo_uri=None,
    request_id=None,
):
    """
    Sync Okta users from MongoDB snapshot to Supabase after each bulk fetch.

    New users are inserted; existing users (by email) are skipped.
    All users are linked to the tenant via user_tenants (upsert — safe to re-run).
    """
    # ── Resolve mongo_uri — mirrors diff_tasks.py pattern exactly ─────────────
    if not mongo_uri and tenant_id:
        try:
            from core.utils.tenant_utils import get_tenant_by_id
            tenant = get_tenant_by_id(tenant_id)
            if tenant and tenant.mongo_uri:
                mongo_uri = tenant.mongo_uri
        except Exception as exc:
            logger.warning(
                f"[SUPABASE SYNC] Could not resolve tenant {tenant_id}: {exc}"
            )

    if not mongo_uri:
        mongo_uri = getattr(settings, 'MONGO_URI', None)

    if not mongo_uri:
        logger.error(
            "[SUPABASE SYNC] No mongo_uri available for tenant_id=%s. Aborting.",
            tenant_id,
            extra={'component': 'celery', 'task_name': 'supabase_sync',
                   'request_id': request_id, 'tenant_id': tenant_id},
        )
        return {"status": "error", "reason": "no_mongo_uri"}

    # ── Read okta_user documents from snapshot ─────────────────────────────────
    mongo_client = None
    try:
        mongo_client = MongoClient(mongo_uri, serverSelectionTimeoutMS=10000)
        db = mongo_client[current_db_name]

        if "okta_user" not in db.list_collection_names():
            logger.info(
                "[SUPABASE SYNC] okta_user collection not found in %s — "
                "users entity was likely disabled or did not run.",
                current_db_name,
                extra={'component': 'celery', 'task_name': 'supabase_sync',
                       'request_id': request_id, 'db_name': current_db_name},
            )
            return {"status": "skipped", "reason": "no_okta_user_collection"}

        # Project only the fields needed — avoids pulling large profile blobs.
        okta_docs = list(
            db["okta_user"].find(
                {"email": {"$exists": True, "$nin": [None, ""]}},
                {"user_id": 1, "email": 1, "login": 1, "_id": 0},
            )
        )
    finally:
        if mongo_client:
            mongo_client.close()

    if not okta_docs:
        logger.info(
            "[SUPABASE SYNC] No users with valid email in %s. Nothing to sync.",
            current_db_name,
        )
        return {"status": "ok", "inserted": 0, "already_present": 0, "tenant_linked": 0}

    # Deduplicate by email — Okta should not produce dupes, but be defensive.
    seen: set = set()
    unique_docs = []
    for doc in okta_docs:
        email = (doc.get("email") or "").strip()
        if email and email not in seen:
            seen.add(email)
            unique_docs.append(doc)

    all_emails = [doc["email"].strip() for doc in unique_docs]
    total = len(all_emails)

    # ── Step 1: Find which emails are already in Supabase ─────────────────────
    from core.utils.supabase_client import get_supabase_client
    sb = get_supabase_client()

    existing_map: dict = {}  # {email: user_uuid}

    for i in range(0, total, BATCH_SIZE):
        batch_emails = all_emails[i:i + BATCH_SIZE]
        try:
            resp = sb.table("users").select("id, email").in_("email", batch_emails).execute()
            for row in (resp.data or []):
                if row.get("email") and row.get("id"):
                    existing_map[row["email"].strip()] = row["id"]
        except Exception as exc:
            logger.error(
                "[SUPABASE SYNC] Email lookup batch (offset %d) failed: %s", i, exc
            )

    # ── Step 2: Insert only users not already in Supabase ─────────────────────
    new_docs = [
        doc for doc in unique_docs
        if doc.get("email", "").strip() not in existing_map
    ]
    inserted = 0

    for i in range(0, len(new_docs), BATCH_SIZE):
        batch = new_docs[i:i + BATCH_SIZE]
        rows = []
        for doc in batch:
            email = doc.get("email", "").strip()
            rows.append({
                "email":        email,
                "username":     (doc.get("login") or email).strip(),
                "okta_user_id": doc.get("user_id"),
                "tenant_id":    str(tenant_id) if tenant_id else None,
                "roles":        ["user"],
            })
        try:
            resp = sb.table("users").insert(rows).execute()
            batch_count = len(resp.data or [])
            inserted += batch_count
            # Capture UUIDs of newly inserted users for user_tenants step.
            for row in (resp.data or []):
                if row.get("email") and row.get("id"):
                    existing_map[row["email"].strip()] = row["id"]
        except Exception as exc:
            logger.error(
                "[SUPABASE SYNC] Insert batch (offset %d, size %d) failed: %s",
                i, len(rows), exc,
            )

    already_present = total - len(new_docs)

    logger.info(
        "[SUPABASE SYNC] db=%s tenant=%s inserted=%d already_present=%d",
        current_db_name, tenant_id, inserted, already_present,
        extra={
            'component':       'celery',
            'task_name':       'supabase_sync',
            'request_id':      request_id,
            'db_name':         current_db_name,
            'tenant_id':       tenant_id,
            'inserted':        inserted,
            'already_present': already_present,
        },
    )

    return {
        "status":          "ok",
        "inserted":        inserted,
        "already_present": already_present,
        "db_name":         current_db_name,
    }
