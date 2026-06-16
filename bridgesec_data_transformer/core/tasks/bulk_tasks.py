import json
import logging
import os
import time
import uuid

import pika
from celery import shared_task, chord
from celery.signals import task_failure, task_revoked
from django.conf import settings

from core.utils.mongo_utils import ensure_mongo_connection, get_dynamic_db
from bridgesec_logging import log_task_start, log_task_complete, log_task_error, log_worker_assignment
from entities.registry import ENTITY_VIEWSETS

logger = logging.getLogger(__name__)


# ── Celery interrupt handlers ──────────────────────────────────────────────────
# These fire when a bulk task raises an unhandled exception or is revoked
# (SIGTERM / celery.control.revoke).  They mark the progress job as failed so
# the SSE stream receives a terminal event and closes instead of polling forever.
# Note: SIGKILL cannot be caught by signals — the stream timeout handles that.

@task_failure.connect(sender='core.tasks.bulk_tasks.run_bulk_entity_task')
@task_failure.connect(sender='core.tasks.bulk_tasks.finalize_bulk_entity_task')
@task_failure.connect(sender='core.tasks.diff_tasks.run_post_bulk_diff_task')
def _on_bulk_task_failure(sender=None, kwargs=None, **kw):
    _kw = kwargs or {}
    request_id = _kw.get('request_id')
    tenant_id = _kw.get('tenant_id')
    if request_id:
        try:
            from core.utils.progress_store import set_job_status
            set_job_status(request_id, 'failed')
            logger.warning(
                "Bulk task failed — job marked as failed via signal",
                extra={'component': 'celery', 'task_name': sender, 'request_id': request_id, 'tenant_id': tenant_id},
            )
        except Exception:
            pass  # never let a signal handler crash the worker


@task_revoked.connect
def _on_task_revoked(request=None, terminated=None, signum=None, **kw):
    _task_kwargs = getattr(request, 'kwargs', None) or {}
    request_id = _task_kwargs.get('request_id')
    tenant_id = _task_kwargs.get('tenant_id')
    if request_id:
        try:
            from core.utils.progress_store import set_job_status
            set_job_status(request_id, 'failed')
            logger.warning(
                "Bulk task revoked — job marked as failed via signal",
                extra={
                    'component':  'celery',
                    'request_id': request_id,
                    'terminated': terminated,
                    'signum':     signum,
                    'tenant_id':  tenant_id,
                },
            )
        except Exception:
            pass


class MockRequest:
    """
    Mock request object to pass Okta access token to viewsets in background tasks.
    This allows Bearer token authentication in Celery tasks without a real Django request.
    """

    def __init__(self, okta_access_token=None, okta_granted_scopes=None):
        self.session = MockSession(okta_access_token, okta_granted_scopes)


class MockSession:
    """Mock session to hold Okta access token for background tasks."""

    def __init__(self, okta_access_token=None, okta_granted_scopes=None):
        self._data = {
            'okta_access_token': okta_access_token,
            'okta_granted_scopes': okta_granted_scopes or [],
        }

    def get(self, key, default=None):
        return self._data.get(key, default)


def notify_backend_via_rabbitmq(db_name, status='completed', error_details=None):
    """
    Notify backend services via RabbitMQ about task completion.
    Enhanced to include status and error information.
    """
    try:
        broker_url = os.getenv("CELERY_BROKER_URL")
        logger.info(f"Connecting to broker: {broker_url}")
        connection = pika.BlockingConnection(pika.URLParameters(broker_url))
        channel = connection.channel()

        channel.queue_declare(queue="task_status", durable=True)

        message_data = {
            "db_name": db_name,
            "status": status
        }
        if error_details:
            message_data["errors"] = error_details

        message = json.dumps(message_data)

        logger.info(f"Sending message to 'task_status': {message}")
        channel.basic_publish(
            exchange="",
            routing_key="task_status",
            body=message,
            properties=pika.BasicProperties(delivery_mode=2),
        )

        logger.info(f"Status message for DB {db_name} sent.")
        connection.close()

    except Exception as e:
        logger.exception(f"Failed to notify via RabbitMQ: {e}")


@shared_task(bind=True)
def process_single_entity_group(self, entity_name, viewset_class_path, db_name, okta_access_token=None, okta_granted_scopes=None, request_id=None, tenant_id=None, disabled_collection_names=None, track_progress=True, mongo_uri=None):
    """
    Process a single entity group in a Celery worker.
    This task runs in parallel with other entity group tasks.

    Args:
        entity_name: Name of the entity group (e.g., 'users', 'groups')
        viewset_class_path: Full module path to viewset class (e.g., 'module.ClassName')
        db_name: Target MongoDB database name
        okta_access_token: OAuth access token (optional)
        okta_granted_scopes: List of granted OAuth scopes
        request_id: Request tracing ID

    Returns:
        Dict with status, entity_name, processing_time, record_counts, error
    """
    start_time = time.time()

    try:
        # Log worker assignment
        worker_id = self.request.id  # Celery task ID
        log_worker_assignment(worker_id, entity_name, request_id)

        if request_id and track_progress:
            from core.utils.progress_store import mark_entity_running
            mark_entity_running(request_id, entity_name, worker_id, mongo_uri=mongo_uri)

        logger.info(
            f"[ENTITY: {entity_name}] Starting processing...",
            extra={
                'component': 'celery',
                'entity_type': entity_name,
                'request_id': request_id,
                'worker_id': worker_id,
            }
        )

        # Import dependencies
        from core.utils.mongo_utils import ensure_mongo_connection
        from importlib import import_module

        # Resolve tenant and ensure MongoDB connection for this worker.
        # Track tenant object so we can attach its URI to mock_request below.
        _resolved_tenant = None
        if tenant_id:
            try:
                from core.utils.tenant_utils import get_tenant_by_id, ensure_mongo_connection_for_tenant, set_current_tenant
                _resolved_tenant = get_tenant_by_id(tenant_id)
                set_current_tenant(_resolved_tenant)
                if _resolved_tenant:
                    ensure_mongo_connection_for_tenant(_resolved_tenant, db_name)
                else:
                    ensure_mongo_connection(db_name)
            except Exception:
                _uri = _resolved_tenant.mongo_uri if (_resolved_tenant and hasattr(_resolved_tenant, 'mongo_uri')) else None
                ensure_mongo_connection(db_name, mongo_uri=_uri)
        else:
            ensure_mongo_connection(db_name)

        # Dynamically import viewset class
        module_path, class_name = viewset_class_path.rsplit('.', 1)
        module = import_module(module_path)
        viewset_class = getattr(module, class_name)

        # Build mock request with all tenant attributes so that:
        #   - okta_base_url resolves the tenant's Okta domain (via _tenant_id)
        #   - store_data() connects to the tenant's MongoDB (via _mongo_uri)
        #   - get_queryset() uses the tenant's DB prefix (via _db_prefix)
        mock_request = MockRequest(okta_access_token, okta_granted_scopes)
        if tenant_id:
            mock_request._tenant_id = tenant_id
        if _resolved_tenant:
            mock_request._mongo_uri  = _resolved_tenant.mongo_uri
            mock_request._db_prefix  = _resolved_tenant.mongo_db_prefix
            mock_request._tenant     = _resolved_tenant

        # Instantiate viewset and fetch data.
        # Set viewset_instance.request so okta_base_url property can resolve the
        # tenant's Okta domain — without this it would fall back to settings.OKTA_API_URL.
        viewset_instance = viewset_class()
        viewset_instance._disabled_collection_names = set(disabled_collection_names or [])
        viewset_instance.request = mock_request
        extracted_data = viewset_instance.fetch_and_store_data(db_name, request=mock_request)

        if not extracted_data:
            if request_id and track_progress:
                from core.utils.progress_store import mark_entity_empty
                mark_entity_empty(request_id, entity_name, mongo_uri=mongo_uri)
            return {
                'status': 'success',
                'entity_name': entity_name,
                'record_counts': {},
                'total_records': 0,
                'processing_time_seconds': time.time() - start_time,
            }

        output_dir = os.path.join(settings.BASE_DIR, "output", db_name)
        os.makedirs(output_dir, exist_ok=True)

        record_counts = {}
        total_records = 0

        for sub_entity_name, sub_entity_data in extracted_data.items():
            file_name = f"{sub_entity_name}.json"
            file_path = os.path.join(output_dir, file_name)

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(sub_entity_data, f, ensure_ascii=False, indent=4)

            record_count = (
                len(sub_entity_data)
                if isinstance(sub_entity_data, list)
                else 1
            )

            record_counts[sub_entity_name] = record_count
            total_records += record_count

        processing_time = time.time() - start_time

        logger.info(
            f"[ENTITY: {entity_name}] ✓ Completed",
            extra={
                'component': 'celery',
                'entity_type': entity_name,
                'request_id': request_id,
                'worker_id': worker_id,
                'record_counts': record_counts,
            }
        )

        if request_id and track_progress:
            if total_records > 0:
                from core.utils.progress_store import update_entity_done
                update_entity_done(request_id, entity_name, record_counts, processing_time, mongo_uri=mongo_uri)
            else:
                from core.utils.progress_store import mark_entity_empty
                mark_entity_empty(request_id, entity_name, mongo_uri=mongo_uri)

        return {
            'status': 'success',
            'entity_name': entity_name,
            'record_counts': record_counts,
            'total_records': total_records,
            'processing_time_seconds': processing_time,
        }

    except Exception as e:
        processing_time = time.time() - start_time

        logger.exception(
            f"[ENTITY: {entity_name}] ✗ Failed: {e}",
            extra={
                'component': 'celery',
                'entity_type': entity_name,
                'request_id': request_id,
                'worker_id': self.request.id,
                'error': str(e),
            }
        )

        if request_id and track_progress:
            from core.utils.progress_store import update_entity_error
            update_entity_error(request_id, entity_name, str(e), mongo_uri=mongo_uri)

        return {
            'status': 'error',
            'entity_name': entity_name,
            'error_message': str(e),
            'record_counts': {},
            'total_records': 0,
            'processing_time_seconds': processing_time
        }


@shared_task
def run_bulk_entity_task(
    okta_access_token=None,
    okta_granted_scopes=None,
    max_workers=4,
    request_id=None,
    db_name=None,
    tenant_id=None,
    track_progress=True,
):
    """
    Dispatches a Celery chord: all entity tasks run in parallel, and
    finalize_bulk_entity_task fires automatically once every one completes.
    Returns immediately after dispatching — no blocking .get() inside a task.

    tenant_id: when provided, only entities enabled for that tenant are backed up.
               When None (single-tenancy mode), uses global entity config.
    track_progress: when True (manual/API runs) the SSE progress job documents are
               written so the frontend can poll. When False (scheduled runs) the
               progress machinery is skipped — the _diff_report is still produced.
    """
    start_time = time.time()

    if not request_id:
        request_id = str(uuid.uuid4())

    # Resolve which entities are enabled for this tenant.
    # Falls back to full ENTITY_VIEWSETS if Supabase is unreachable or catalog is empty.
    from core.utils.entity_config import get_enabled_entities_for_tenant, get_disabled_collections_for_tenant
    enabled_names = get_enabled_entities_for_tenant(tenant_id)
    entity_viewsets = {k: v for k, v in ENTITY_VIEWSETS.items() if k in enabled_names}
    disabled_collections = get_disabled_collections_for_tenant(tenant_id)

    # total_groups derived from filtered set so progress bar stays accurate
    total_groups = len(entity_viewsets)

    # db_name is pre-generated by the view and passed here so both the job doc
    # and the actual data end up under the same DB name.
    # For scheduled tasks (no view involvement) generate it here instead.
    job_created_by_view = db_name is not None
    if not db_name:
        db_name = get_dynamic_db()

    log_task_start(
        'bulk_fetch',
        params={'total_groups': total_groups, 'db_name': db_name, 'tenant_id': tenant_id},
        request_id=request_id
    )

    logger.info(
        "PARALLEL BULK FETCH STARTING (Celery Chord)",
        extra={
            'component':    'celery',
            'task_name':    'bulk_fetch',
            'request_id':   request_id,
            'db_name':      db_name,
            'total_groups': total_groups,
            'tenant_id':    tenant_id,
        }
    )

    if okta_access_token:
        logger.info("Using Bearer token authentication (user's OAuth token)")
        logger.info(f"Granted scopes: {okta_granted_scopes}")
    else:
        logger.info("Using SSWS token authentication (static API token fallback)")

    try:
        _chord_mongo_uri = None
        if tenant_id:
            try:
                from core.utils.tenant_utils import get_tenant_by_id, set_current_tenant
                _t = get_tenant_by_id(tenant_id)
                if _t:
                    _chord_mongo_uri = _t.mongo_uri
                    set_current_tenant(_t)
            except Exception:
                pass
        ensure_mongo_connection(db_name, mongo_uri=_chord_mongo_uri)
        logger.info(f"MongoDB connection established for db_name={db_name}")

        # For view-triggered runs, create_bulk_job was already called synchronously
        # in bulk_view.post() before .delay() — job doc already exists.
        # For scheduled tasks (no view), create it here — but only when progress
        # tracking is on. Scheduled runs (track_progress=False) skip the SSE job doc.
        if track_progress and not job_created_by_view:
            from core.utils.progress_store import create_bulk_job
            create_bulk_job(request_id, db_name, list(entity_viewsets.keys()), mongo_uri=_chord_mongo_uri)

        tasks = []
        for entity_name, viewset_class in entity_viewsets.items():
            viewset_class_path = f"{viewset_class.__module__}.{viewset_class.__name__}"
            tasks.append(
                process_single_entity_group.s(
                    entity_name=entity_name,
                    viewset_class_path=viewset_class_path,
                    db_name=db_name,
                    okta_access_token=okta_access_token,
                    okta_granted_scopes=okta_granted_scopes,
                    request_id=request_id,
                    tenant_id=tenant_id,
                    disabled_collection_names=list(disabled_collections.get(entity_name, set())),
                    track_progress=track_progress,
                    mongo_uri=_chord_mongo_uri,
                )
            )

        logger.info(f"Dispatching chord of {len(tasks)} entity tasks...")
        # Thread the exact mongo_uri this bulk run wrote to all the way into the
        # diff task so it reads/writes the SAME cluster — never re-resolving and
        # risking a different cluster (the cause of the missing scheduled diff).
        chord(tasks)(
            finalize_bulk_entity_task.s(
                db_name=db_name,
                request_id=request_id,
                start_time_epoch=start_time,
                tenant_id=tenant_id,
                mongo_uri=_chord_mongo_uri,
                track_progress=track_progress,
            )
        )

        logger.info(
            "Chord dispatched — finalize_bulk_entity_task will run after all entity tasks complete",
            extra={
                'component':    'celery',
                'task_name':    'bulk_fetch',
                'request_id':   request_id,
                'db_name':      db_name,
                'total_groups': total_groups,
            }
        )

        return {
            "status":       "dispatched",
            "db_name":      db_name,
            "total_groups": total_groups,
            "request_id":   request_id,
        }

    except Exception as e:
        logger.exception(
            f"Error dispatching bulk entity chord for db {db_name}: {e}",
            extra={
                'component':  'celery',
                'task_name':  'bulk_fetch',
                'request_id': request_id,
                'db_name':    db_name,
            }
        )
        notify_backend_via_rabbitmq(db_name, 'failed', [{'entity': 'main_task', 'error': str(e)}])
        return {"status": "error", "db_name": db_name, "error": str(e)}


@shared_task
def finalize_bulk_entity_task(entity_results, db_name, request_id, start_time_epoch, tenant_id=None, mongo_uri=None, track_progress=True):
    """
    Chord callback — Celery triggers this automatically once ALL
    process_single_entity_group tasks have completed.

    Aggregates results, writes the _bulk_status marker, notifies RabbitMQ,
    and queues run_post_bulk_diff_task.

    Args:
        entity_results:   List of return dicts from process_single_entity_group,
                          passed automatically by Celery chord.
        db_name:          MongoDB database name for this bulk run.
        request_id:       Tracing ID from the parent task.
        start_time_epoch: Unix timestamp recorded before chord dispatch,
                          used to compute total wall-clock time.
    """
    if tenant_id:
        try:
            from core.utils.tenant_utils import get_tenant_by_id, set_current_tenant
            set_current_tenant(get_tenant_by_id(tenant_id))
        except Exception:
            pass

    total_groups = len(ENTITY_VIEWSETS)

    # ── Aggregate results ──────────────────────────────────────────────────────
    successful = 0
    failed = 0
    error_details = []

    for res in (entity_results or []):
        if res.get('status') == 'success':
            successful += 1
            logger.info(
                f"✓ {res['entity_name']}: {res.get('processing_time_seconds', 0):.2f}s",
                extra={'component': 'celery', 'request_id': request_id, 'tenant_id': tenant_id},
            )
        else:
            failed += 1
            error_details.append({
                'entity': res.get('entity_name', 'unknown'),
                'error':  res.get('error_message', 'Unknown error'),
            })
            logger.error(
                f"✗ {res.get('entity_name', 'unknown')}: "
                f"{res.get('error_message', 'Unknown error')}",
                extra={'component': 'celery', 'request_id': request_id, 'tenant_id': tenant_id},
            )

    if failed == 0 and successful > 0:
        overall_status = 'success'
        notify_status  = 'completed'
    elif successful > 0:
        overall_status = 'partial_success'
        notify_status  = 'partial_completed'
    else:
        overall_status = 'error'
        notify_status  = 'failed'

    total_time = time.time() - start_time_epoch
    duration_ms = int(total_time * 1000)

    log_task_complete(
        'bulk_fetch',
        result={
            'status':       overall_status,
            'successful':   successful,
            'failed':       failed,
            'total_groups': total_groups,
        },
        duration_ms=duration_ms,
        request_id=request_id,
    )

    logger.info(
        "PARALLEL BULK FETCH COMPLETED",
        extra={
            'component':         'celery',
            'task_name':         'bulk_fetch',
            'request_id':        request_id,
            'status':            overall_status,
            'successful_groups': successful,
            'failed_groups':     failed,
            'total_groups':      total_groups,
            'duration_ms':       duration_ms,
        }
    )

    # ── Notify RabbitMQ ────────────────────────────────────────────────────────
    notify_backend_via_rabbitmq(db_name, notify_status, error_details if error_details else None)

    # ── Transition to diff_running so SSE stays alive while the diff runs ────────
    # The diff task calls set_job_completed(request_id, {full summary}) when it
    # finishes, which is when the SSE stream delivers its terminal "complete" event
    # carrying the populated diff_summary.  If the diff task fails, the
    # @task_failure.connect signal handler sets status="failed" instead.
    if track_progress:
        from core.utils.progress_store import set_job_status
        set_job_status(request_id, "diff_running", mongo_uri=mongo_uri)

    try:
        from celery import current_app
        current_app.send_task(
            'core.tasks.diff_tasks.run_post_bulk_diff_task',
            kwargs={
                'current_db_name': db_name,
                'request_id':      request_id,
                'tenant_id':       tenant_id,
                'mongo_uri':       mongo_uri,
                'track_progress':  track_progress,
            },
        )
        logger.info(
            "Post-bulk diff task queued",
            extra={
                'component':   'celery',
                'task_name':   'post_bulk_diff',
                'request_id':  request_id,
                'db_name':     db_name,
                'bulk_status': overall_status,
                'tenant_id':   tenant_id,
            }
        )
    except Exception as send_err:
        logger.error(
            f"Could not queue post-bulk diff task: {send_err}",
            extra={
                'component':  'celery',
                'task_name':  'post_bulk_diff',
                'request_id': request_id,
                'db_name':    db_name,
                'tenant_id':  tenant_id,
            }
        )
        # SSE is already closed as 'completed' — no status update needed here

    try:
        from celery import current_app
        current_app.send_task(
            'core.tasks.supabase_sync_tasks.sync_okta_users_to_supabase',
            kwargs={
                'current_db_name': db_name,
                'tenant_id':       tenant_id,
                'mongo_uri':       mongo_uri,
                'request_id':      request_id,
            },
        )
        logger.info(
            "Post-bulk Supabase user sync task queued",
            extra={
                'component':  'celery',
                'task_name':  'supabase_sync',
                'request_id': request_id,
                'db_name':    db_name,
                'tenant_id':  tenant_id,
            }
        )
    except Exception as send_err:
        logger.error(
            f"Could not queue Supabase user sync task: {send_err}",
            extra={
                'component':  'celery',
                'task_name':  'supabase_sync',
                'request_id': request_id,
                'db_name':    db_name,
                'tenant_id':  tenant_id,
            }
        )

    return {
        "status":            overall_status,
        "db_name":           db_name,
        "total_groups":      total_groups,
        "successful_groups": successful,
        "failed_groups":     failed,
        "total_time_seconds": total_time,
        "errors":            error_details if error_details else None,
    }


@shared_task
def run_scheduled_bulk_task_for_tenant(tenant_id: str):
    """
    Scheduled bulk fetch for a single tenant. Called directly by Celery Beat at
    the exact UTC time derived from the tenant's scheduler_hour/minute/timezone
    (registered at Beat startup via beat_init in celery.py).

    No time-checking needed here — if Beat called this task, it is time to run.
    The tenant is re-fetched from Supabase so a scheduler_enabled=False change
    made after Beat started is still honoured.
    """
    import datetime as _dt
    from core.utils.supabase_tenant import SupabaseTenant
    from core.utils.tenant_service_token import get_service_access_token_for_tenant

    logger.info(
        f"Scheduled bulk fetch triggered for tenant {tenant_id}",
        extra={'component': 'celery', 'task_name': 'scheduled_bulk_fetch', 'tenant_id': tenant_id}
    )

    tenant = SupabaseTenant.get_by_id(tenant_id)
    if not tenant:
        logger.error(
            f"Scheduled bulk fetch: tenant {tenant_id} not found in Supabase.",
            extra={'component': 'celery', 'task_name': 'scheduled_bulk_fetch', 'tenant_id': tenant_id}
        )
        return {"status": "error", "reason": "tenant_not_found"}

    if not tenant.scheduler_enabled:
        logger.info(
            f"Scheduled bulk fetch skipped for tenant '{tenant.name}' — scheduler_enabled=False",
            extra={'component': 'celery', 'task_name': 'scheduled_bulk_fetch', 'tenant_id': tenant_id}
        )
        return {"status": "skipped", "reason": "scheduler_disabled"}

    # Slot-claim dedup: prevents double dispatch if Beat retries the task or
    # APScheduler and Beat both fire in the same minute.
    slot_key = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H%M")
    if not SupabaseTenant.try_claim_scheduled_slot(tenant.id, slot_key):
        logger.info(
            f"Tenant '{tenant.name}' skipped — slot {slot_key} already claimed (duplicate trigger)",
            extra={'component': 'celery', 'task_name': 'scheduled_bulk_fetch', 'tenant_id': tenant_id}
        )
        return {"status": "skipped", "reason": "already_ran", "slot": slot_key}

    try:
        access_token, granted_scopes = get_service_access_token_for_tenant(tenant)
        logger.info(
            f"Service token obtained for tenant '{tenant.name}'. Dispatching bulk task.",
            extra={'component': 'celery', 'task_name': 'scheduled_bulk_fetch', 'tenant_id': tenant_id}
        )
        run_bulk_entity_task.delay(
            okta_access_token=access_token,
            okta_granted_scopes=granted_scopes,
            tenant_id=str(tenant.id),
            track_progress=False,
        )
        return {"status": "dispatched", "tenant": tenant.name}
    except Exception as e:
        logger.exception(
            f"Scheduled bulk fetch failed for tenant '{tenant.name}': {e}",
            extra={'component': 'celery', 'task_name': 'scheduled_bulk_fetch', 'tenant_id': tenant_id}
        )
        return {"status": "error", "error": str(e)}


@shared_task
def run_bulk_entity_task_sequential(okta_access_token=None, okta_granted_scopes=None):
    """
    DEPRECATED: Original sequential implementation.
    Kept for fallback/testing purposes. Use run_bulk_entity_task instead.

    Background task to fetch data from all Okta entities and store in MongoDB (sequential).

    Args:
        okta_access_token: Optional OAuth access token from user session.
                          If provided, uses Bearer token authentication.
                          If None, falls back to SSWS API token.
        okta_granted_scopes: List of OAuth scopes granted to the access token.
    """
    db_name = get_dynamic_db()
    logger.info(f"[TASK START] run_bulk_entity_task_sequential triggered with db_name={db_name}")

    # Log authentication method being used
    if okta_access_token:
        logger.info("Using Bearer token authentication (user's OAuth token)")
        logger.info(f"Granted scopes: {okta_granted_scopes}")
    else:
        logger.info("Using SSWS token authentication (static API token fallback)")

    # Create mock request object to pass token and scopes to viewsets
    mock_request = MockRequest(
        okta_access_token=okta_access_token,
        okta_granted_scopes=okta_granted_scopes
    ) if okta_access_token else None

    try:
        # Ensure MongoDB connection
        ensure_mongo_connection(db_name)
        logger.info(f"MongoDB connection established for db_name={db_name}")

        # Process each entity
        for entity_name, viewset_class in ENTITY_VIEWSETS.items():
            logger.info(f"Processing entity: {entity_name}")
            viewset_instance = viewset_class()

            # Pass mock request with access token to enable Bearer authentication
            extracted_data = viewset_instance.fetch_and_store_data(db_name, request=mock_request)

            if not extracted_data:
                logger.error(f"Failed to fetch {entity_name} data")
                continue

            # Create output directory
            output_dir = os.path.join(settings.BASE_DIR, "output", db_name)
            os.makedirs(output_dir, exist_ok=True)

            # Save data to JSON files
            for sub_entity_name, sub_entity_data in extracted_data.items():
                file_name = f"{sub_entity_name}.json"
                file_path = os.path.join(output_dir, file_name)

                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(sub_entity_data, f, ensure_ascii=False, indent=4)

                logger.info(f"Saved {sub_entity_name} data to {file_path}")

        logger.info(f"[TASK COMPLETED] All data stored for DB: {db_name}")
        notify_backend_via_rabbitmq(db_name)
        return {"status": "success", "db_name": db_name}

    except Exception as e:
        logger.exception(f"Error during bulk entity fetch for db {db_name}: {e}")
        return {"status": "error", "db_name": db_name, "error": str(e)}
