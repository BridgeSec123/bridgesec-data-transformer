import logging
import time
from datetime import datetime, timedelta, timezone

from celery import shared_task
from django.conf import settings
from pymongo import MongoClient

from bridgesec_logging import log_task_start, log_task_complete, log_task_error, log_worker_assignment
from core.utils.mapping_provider import get_entity_id_mapping, get_resource_collection_map
from core.utils.db_utils import compute_entity_diff_summary, get_previous_db
from entities.services.resouce_data_service import EntityDataService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=0)
def run_post_bulk_diff_task(self, current_db_name, request_id=None, tenant_id=None,
                            mongo_uri=None, track_progress=True):
    """
    Post-bulk-fetch change detection task.

    Iterates over every entity in ENTITY_ID_MAPPING and writes a diff document
    for every entity that appears in at least one of the two snapshots:

      presence="both"             — entity exists in both; normal add/remove/modify diff
      presence="only_in_previous" — entity disappeared; all records shown as removed
      presence="only_in_current"  — entity newly appeared; all records shown as added

    Entities absent from BOTH snapshots are skipped (no doc written). An
    aggregate `summary` document is always written.

    Triggered by finalize_bulk_entity_task after the chord completes.
    max_retries=0: partial results are already stored on failure; a retry would
    redundantly re-run the entire entity loop.
    """
    start_time = time.time()

    # Prefer the mongo_uri the bulk pipeline actually wrote to — threaded through
    # finalize_bulk_entity_task. Re-resolving the tenant here can connect to a
    # DIFFERENT cluster than the snapshot data lives on, which is the cause of the
    # missing scheduled _diff_report: the report would be written to the wrong
    # cluster (or the task would raise). We only re-resolve as a fallback.
    uri_from_bulk = bool(mongo_uri)
    db_prefix = None
    if tenant_id:
        try:
            from core.utils.tenant_utils import get_tenant_by_id, set_current_tenant
            tenant = get_tenant_by_id(tenant_id)
            if tenant:
                if not mongo_uri:
                    mongo_uri = tenant.mongo_uri
                db_prefix = tenant.mongo_db_prefix
                set_current_tenant(tenant)
        except Exception as e:
            logger.warning(f"[DIFF] Could not resolve tenant {tenant_id}: {e}")

    if not mongo_uri:
        # Last resort — system URI from .env, or raise if nothing is configured.
        mongo_uri = getattr(settings, 'MONGO_URI', None) or None
    if not mongo_uri:
        raise ValueError(
            f"Diff task: no mongo_uri for tenant_id={tenant_id}. "
            "In multi-tenant mode ensure the tenant has mongo_uri configured in Supabase."
        )

    if not db_prefix:
        db_prefix = settings.MONGO_DB_NAME

    # Create a fresh MongoClient in this worker process.
    # settings.MONGO_CLIENT is created at Django import time in the parent Celery
    # process and inherited by forked workers — PyMongo's connection pool is not
    # fork-safe, so the first network call (list_database_names) would time out or
    # fail with ServerSelectionTimeoutError.  A new client avoids that entirely.
    mongo_client = MongoClient(mongo_uri, serverSelectionTimeoutMS=10000)
    diff_collection = mongo_client[current_db_name]["_diff_report"]

    # Diagnostic: log which cluster we connected to and how many prefix-matching
    # snapshots it can see, so a future cluster misconnection is obvious from logs.
    try:
        from urllib.parse import urlparse
        _host = urlparse(mongo_uri).hostname or "?"
    except Exception:
        _host = "?"
    try:
        _visible_snapshots = [d for d in mongo_client.list_database_names()
                              if d.startswith(f"{db_prefix}_")]
    except Exception:
        _visible_snapshots = []
    logger.info(
        f"[DIFF] connected host={_host} uri_source={'bulk' if uri_from_bulk else 'resolved'} "
        f"visible {db_prefix}_ snapshots={len(_visible_snapshots)}",
        extra={
            'component':              'celery',
            'task_name':              'post_bulk_diff',
            'request_id':             request_id,
            'db_name':                current_db_name,
            'mongo_host':             _host,
            'visible_snapshot_count': len(_visible_snapshots),
        },
    )

    # ── Task lifecycle start ────────────────────────────────────────────────
    log_task_start(
        'post_bulk_diff',
        params={'current_db': current_db_name, 'entity_count': len(get_entity_id_mapping())},
        request_id=request_id
    )
    logger.info(
        "Post-bulk diff task started",
        extra={
            'component':  'celery',
            'task_name':  'post_bulk_diff',
            'request_id': request_id,
            'db_name':    current_db_name,
        }
    )

    try:
        # ── Find previous snapshot ──────────────────────────────────────────
        previous_db_name = get_previous_db(mongo_client, current_db_name, prefix=db_prefix)

        if previous_db_name:
            logger.info(
                f"[DIFF] ━━━  {previous_db_name}  →  {current_db_name}  ━━━",
                extra={
                    'component':    'celery',
                    'task_name':    'post_bulk_diff',
                    'request_id':   request_id,
                    'current_db':   current_db_name,
                    'previous_db':  previous_db_name,
                }
            )

        if not previous_db_name:
            diff_collection.replace_one(
                {"_id": "summary"},
                {
                    "_id":              "summary",
                    "type":             "summary",
                    "is_first_snapshot": True,
                    "current_db":       current_db_name,
                    "previous_db":      None,
                    "generated_at":     datetime.now(timezone.utc).isoformat(),
                    "request_id":       request_id,
                },
                upsert=True,
            )
            logger.info(
                "[DIFF] First snapshot — no previous DB found. Diff skipped.",
                extra={
                    "component":  "celery",
                    "task_name":  "post_bulk_diff",
                    "request_id": request_id,
                    "db_name":    current_db_name,
                },
            )
            # Sanity check: "no previous" while the connected cluster clearly holds
            # multiple snapshots almost always means we connected to the WRONG cluster.
            if len(_visible_snapshots) >= 2:
                logger.warning(
                    f"[DIFF] No previous DB resolved, yet {len(_visible_snapshots)} "
                    f"'{db_prefix}_' snapshots are visible on host={_host}. "
                    f"This usually means the diff connected to a different cluster than "
                    f"the bulk write. current_db={current_db_name}",
                    extra={
                        "component":              "celery",
                        "task_name":              "post_bulk_diff",
                        "request_id":             request_id,
                        "db_name":                current_db_name,
                        "mongo_host":             _host,
                        "visible_snapshot_count": len(_visible_snapshots),
                    },
                )
            if track_progress:
                from core.utils.progress_store import set_job_completed
                set_job_completed(request_id, {"is_first_snapshot": True}, mongo_uri=mongo_uri)

            log_task_complete(
                'post_bulk_diff',
                result={'status': 'first_snapshot', 'db_name': current_db_name},
                duration_ms=int((time.time() - start_time) * 1000),
                request_id=request_id
            )
            return {"status": "first_snapshot", "db_name": current_db_name}

        # ── Per-entity comparison loop ──────────────────────────────────────
        service = EntityDataService(mongo_client=mongo_client)
        entity_summaries   = {}   # entities with at least one-sided presence
        total_added        = 0
        total_removed      = 0
        total_modified     = 0
        total_unchanged    = 0
        entities_with_changes = 0
        entities_skipped   = 0
        entity_errors      = []

        # Fetch collection names from both DBs once — used for sub_collections presence below.
        current_collections  = set(mongo_client[current_db_name].list_collection_names())
        previous_collections = set(mongo_client[previous_db_name].list_collection_names())

        # Build reverse lookup: entity display name → all sibling sub-collections in its category.
        # Example: "Users" and "User Schema Properties" both map to the full "Users" category dict.
        entity_to_subs: dict = {}
        for category_subs in get_resource_collection_map().values():
            flat = {}
            for sub_dict in category_subs:
                flat.update(sub_dict)        # {display_name: collection_name}
            for display_name in flat:
                entity_to_subs[display_name] = flat

        for entity_key, id_field in get_entity_id_mapping().items():

            try:
                # db_name is passed directly so date_str ("") is unused
                # (resouce_data_service.py lines 57-58)
                fetch_start = time.time()
                old_docs = service.fetch("", entity_key, db_name=previous_db_name)
                new_docs = service.fetch("", entity_key, db_name=current_db_name)
                fetch_ms = int((time.time() - fetch_start) * 1000)

                logger.info(
                    f"[DIFF] {entity_key}: fetched {len(old_docs)} old / {len(new_docs)} new  ({fetch_ms}ms)",
                    extra={
                        'component':  'celery',
                        'task_name':  'post_bulk_diff',
                        'request_id': request_id,
                        'entity':     entity_key,
                        'fetch_ms':   fetch_ms,
                        'old_count':  len(old_docs),
                        'new_count':  len(new_docs),
                    }
                )

                # Skip only when both sides are empty (entity absent from both snapshots).
                # One-sided presence is a meaningful signal: the entity disappeared from
                # or newly appeared in the current snapshot — record it in the report.
                if not old_docs and not new_docs:
                    entities_skipped += 1
                    logger.info(
                        f"[DIFF] {entity_key}: skipped — absent from both snapshots",
                        extra={
                            'component':  'celery',
                            'task_name':  'post_bulk_diff',
                            'request_id': request_id,
                            'entity':     entity_key,
                        }
                    )
                    continue

                # Determine where this entity lives across the two snapshots.
                if old_docs and not new_docs:
                    presence = "only_in_previous"   # disappeared from current snapshot
                elif not old_docs and new_docs:
                    presence = "only_in_current"    # newly appeared in current snapshot
                else:
                    presence = "both"               # normal case — present in both

                if presence != "both":
                    logger.info(
                        f"[DIFF] {entity_key}: presence={presence} "
                        f"(old={len(old_docs)}, new={len(new_docs)}) — recording one-sided diff",
                        extra={
                            'component':  'celery',
                            'task_name':  'post_bulk_diff',
                            'request_id': request_id,
                            'entity':     entity_key,
                            'presence':   presence,
                        }
                    )

                # compute_entity_diff_summary handles empty lists correctly:
                #   old=[], new=[records] → all records in added_ids
                #   old=[records], new=[] → all records in removed_ids
                diff = compute_entity_diff_summary(old_docs, new_docs, id_field, entity_key)

                # Skip entities that produced zero records on both sides.
                # Happens when the id_field is absent from all documents (e.g. singleton
                # configs whose field name doesn't match) or the collection is genuinely
                # empty in both snapshots — no value in including them in the summary.
                if diff["total_current"] == 0 and diff["total_previous"] == 0:
                    entities_skipped += 1
                    logger.info(
                        f"[DIFF] {entity_key}: skipped — zero records in both snapshots",
                        extra={'component': 'celery', 'task_name': 'post_bulk_diff',
                               'request_id': request_id, 'entity': entity_key},
                    )
                    continue

                # Log each added / removed / modified record so the worker
                # console shows exactly which IDs changed and what fields.
                for added_id in diff["added_ids"]:
                    logger.info(
                        f"[DIFF] {entity_key} ＋ added    {id_field}={added_id}",
                        extra={'component': 'celery', 'task_name': 'post_bulk_diff',
                               'request_id': request_id, 'entity': entity_key},
                    )
                for removed_id in diff["removed_ids"]:
                    logger.info(
                        f"[DIFF] {entity_key} － removed  {id_field}={removed_id}",
                        extra={'component': 'celery', 'task_name': 'post_bulk_diff',
                               'request_id': request_id, 'entity': entity_key},
                    )
                for item in diff["modified"]:
                    item_id     = item.get(id_field, "?")
                    change_keys = list(item.get("changes", {}).keys())
                    logger.info(
                        f"[DIFF] {entity_key} ～ modified {id_field}={item_id}  "
                        f"changed_fields={change_keys}",
                        extra={'component': 'celery', 'task_name': 'post_bulk_diff',
                               'request_id': request_id, 'entity': entity_key},
                    )

                if diff["truncated"]:
                    logger.warning(
                        f"[DIFF] {entity_key}: modified list truncated to 500 "
                        f"(actual modified_count={diff['modified_count']})",
                        extra={
                            'component':     'celery',
                            'task_name':     'post_bulk_diff',
                            'request_id':    request_id,
                            'entity':        entity_key,
                            'modified_count': diff['modified_count'],
                        }
                    )

                # Store per-entity diff document
                diff_collection.replace_one(
                    {"_id": entity_key},
                    {
                        "_id":         entity_key,
                        "type":        "entity_diff",
                        "entity_name": entity_key,
                        "id_field":    id_field,
                        "presence":    presence,
                        "current_db":  current_db_name,
                        "previous_db": previous_db_name,
                        **diff,
                    },
                    upsert=True,
                )

                # Accumulate aggregate totals
                total_added     += diff["added_count"]
                total_removed   += diff["removed_count"]
                total_modified  += diff["modified_count"]
                total_unchanged += diff["unchanged_count"]

                has_changes = (
                    diff["added_count"]    > 0
                    or diff["removed_count"]  > 0
                    or diff["modified_count"] > 0
                )
                if has_changes:
                    entities_with_changes += 1

                # Populate entity_summaries for every stored entity diff
                # (both-sides, one-side) so the summary lists every compared entity.
                entity_summaries[entity_key] = {
                    "presence":       presence,
                    "added":          diff["added_count"],
                    "removed":        diff["removed_count"],
                    "modified":       diff["modified_count"],
                    "unchanged":      diff["unchanged_count"],
                    "total_current":  diff["total_current"],
                    "total_previous": diff["total_previous"],
                    "net_change":     diff["net_change"],
                    "has_changes":    has_changes,
                }

                # Attach sub-collection presence for every sibling collection in this
                # entity's RESOURCE_COLLECTION_MAP category.
                # Only collections present in at least one snapshot are included.
                category_subs = entity_to_subs.get(entity_key, {})
                if category_subs:
                    sub_collections = {
                        display: {
                            "in_current":  collection in current_collections,
                            "in_previous": collection in previous_collections,
                        }
                        for display, collection in category_subs.items()
                        if collection in current_collections or collection in previous_collections
                    }
                    if sub_collections:
                        entity_summaries[entity_key]["sub_collections"] = sub_collections

                logger.info(
                    f"[DIFF] {entity_key}: "
                    f"+{diff['added_count']} added  "
                    f"-{diff['removed_count']} removed  "
                    f"~{diff['modified_count']} modified  "
                    f"={diff['unchanged_count']} unchanged",
                    extra={
                        "component":  "celery",
                        "task_name":  "post_bulk_diff",
                        "request_id": request_id,
                        "entity":     entity_key,
                        "added":      diff["added_count"],
                        "removed":    diff["removed_count"],
                        "modified":   diff["modified_count"],
                        "unchanged":  diff["unchanged_count"],
                    },
                )

            except Exception as e:
                logger.exception(
                    f"[DIFF] Error comparing entity '{entity_key}': {e}",
                    extra={"component": "celery", "request_id": request_id},
                )
                entity_errors.append({"entity": entity_key, "error": str(e)})
                continue  # one entity failure must never abort the full loop

        # ── Store summary document ──────────────────────────────────────────
        comparison_time = round(time.time() - start_time, 2)

        diff_collection.replace_one(
            {"_id": "summary"},
            {
                "_id":                      "summary",
                "type":                     "summary",
                "is_first_snapshot":        False,
                "current_db":               current_db_name,
                "previous_db":              previous_db_name,
                "generated_at":             datetime.now(timezone.utc).isoformat(),
                "request_id":               request_id,
                "total_entities_compared":  len(entity_summaries),
                "entities_skipped":         entities_skipped,
                "entities_with_changes":    entities_with_changes,
                "total_added":              total_added,
                "total_removed":            total_removed,
                "total_modified":           total_modified,
                "total_unchanged":          total_unchanged,
                "comparison_time_seconds":  comparison_time,
                "entity_errors":            entity_errors,
                # All entities with at least one-sided presence (both / only_in_previous / only_in_current).
                "entity_summaries":         entity_summaries,
            },
            upsert=True,
        )

        if track_progress:
            from core.utils.progress_store import set_job_completed
            set_job_completed(request_id, {
                "is_first_snapshot":       False,
                "current_db":              current_db_name,
                "previous_db":             previous_db_name,
                "generated_at":            datetime.now(timezone.utc).isoformat(),
                "total_entities_compared": len(entity_summaries),
                "entities_with_changes":   entities_with_changes,
                "total_added":             total_added,
                "total_removed":           total_removed,
                "total_modified":          total_modified,
                "total_unchanged":         total_unchanged,
                "entity_summaries":        entity_summaries,
            }, mongo_uri=mongo_uri)

        logger.info(
            "[DIFF] Summary document stored in _diff_report",
            extra={
                'component':               'celery',
                'task_name':               'post_bulk_diff',
                'request_id':              request_id,
                'db_name':                 current_db_name,
                'total_entities_compared': len(entity_summaries),
                'entities_with_changes':   entities_with_changes,
                'entities_skipped':        entities_skipped,
                'entity_error_count':      len(entity_errors),
            }
        )

        logger.info(
            "[DIFF] Completed",
            extra={
                "component":               "celery",
                "task_name":               "post_bulk_diff",
                "request_id":              request_id,
                "db_name":                 current_db_name,
                "previous_db":             previous_db_name,
                "entities_with_changes":   entities_with_changes,
                "comparison_time_seconds": comparison_time,
            },
        )

        overall_status = "completed" if not entity_errors else "partial"
        duration_ms = int(comparison_time * 1000)

        log_task_complete(
            'post_bulk_diff',
            result={
                'status':                overall_status,
                'entities_compared':     len(entity_summaries),
                'entities_with_changes': entities_with_changes,
                'total_added':           total_added,
                'total_removed':         total_removed,
                'total_modified':        total_modified,
                'entity_errors':         len(entity_errors),
            },
            duration_ms=duration_ms,
            request_id=request_id
        )

        return {
            "status":                  overall_status,
            "current_db":              current_db_name,
            "previous_db":             previous_db_name,
            "entities_compared":       len(entity_summaries),
            "entities_with_changes":   entities_with_changes,
            "total_added":             total_added,
            "total_removed":           total_removed,
            "total_modified":          total_modified,
            "comparison_time_seconds": comparison_time,
            "errors":                  entity_errors or None,
        }

    except Exception as e:
        # Job is 'diff_running' at this point; the @task_failure.connect signal
        # handler in bulk_tasks.py sets it to 'failed' so the SSE terminates.
        log_task_error(
            'post_bulk_diff',
            error=str(e),
            request_id=request_id
        )
        logger.exception(
            f"[DIFF] Unexpected task failure: {e}",
            extra={
                'component':  'celery',
                'task_name':  'post_bulk_diff',
                'request_id': request_id,
                'db_name':    current_db_name,
            }
        )
        raise  # re-raise so Celery marks task FAILED and records traceback

    finally:
        # Chord results are no longer needed — clean up to save space.
        # Runs unconditionally: covers first-snapshot early return, normal completion, and failures.
        try:
            # IMPORTANT: only purge results that have been done for a while. A blanket
            # delete_many({}) here would wipe in-flight chord/group state for OTHER jobs
            # still aggregating results on the shared backend, breaking their callbacks.
            cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
            stale_filter = {"date_done": {"$lt": cutoff}}
            deleted_meta  = mongo_client["celery_results"]["celery_taskmeta"].delete_many(stale_filter)
            deleted_group = mongo_client["celery_results"]["celery_groupmeta"].delete_many(stale_filter)
            logger.info(
                f"[DIFF] Cleaned up {deleted_meta.deleted_count} stale task result(s) from celery_taskmeta, "
                f"{deleted_group.deleted_count} stale chord state(s) from celery_groupmeta",
                extra={'component': 'celery', 'task_name': 'post_bulk_diff', 'request_id': request_id}
            )
        except Exception as cleanup_err:
            logger.warning(
                f"[DIFF] Celery result cleanup failed (non-fatal): {cleanup_err}",
                extra={'component': 'celery', 'task_name': 'post_bulk_diff', 'request_id': request_id}
            )
        mongo_client.close()  # always release connection pool sockets
