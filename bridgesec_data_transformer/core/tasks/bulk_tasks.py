import json
import logging
import os
import time

import pika
from celery import shared_task, group
from django.conf import settings

from core.utils.mongo_utils import ensure_mongo_connection, get_dynamic_db
from entities.registry import ENTITY_VIEWSETS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
def process_single_entity_group(self, entity_name, viewset_class_path, db_name, okta_access_token=None, okta_granted_scopes=None):
    """
    Process a single entity group in a Celery worker.
    This task runs in parallel with other entity group tasks.

    Args:
        entity_name: Name of the entity group (e.g., 'users', 'groups')
        viewset_class_path: Full module path to viewset class (e.g., 'module.ClassName')
        db_name: Target MongoDB database name
        okta_access_token: OAuth access token (optional)
        okta_granted_scopes: List of granted OAuth scopes

    Returns:
        Dict with status, entity_name, processing_time, record_counts, error
    """
    start_time = time.time()

    try:
        logger.info(f"[ENTITY: {entity_name}] Starting processing...")

        # Import dependencies
        from core.utils.mongo_utils import ensure_mongo_connection
        from importlib import import_module

        # Ensure MongoDB connection for this worker
        ensure_mongo_connection(db_name)

        # Dynamically import viewset class
        module_path, class_name = viewset_class_path.rsplit('.', 1)
        module = import_module(module_path)
        viewset_class = getattr(module, class_name)

        # Create mock request for OAuth token
        mock_request = None
        if okta_access_token:
            mock_request = MockRequest(okta_access_token, okta_granted_scopes)

        # Instantiate viewset and fetch data
        viewset_instance = viewset_class()
        extracted_data = viewset_instance.fetch_and_store_data(db_name, request=mock_request)

        if not extracted_data:
            logger.warning(f"[ENTITY: {entity_name}] No data extracted")
            return {
                'status': 'success',
                'entity_name': entity_name,
                'extracted_data': {},
                'record_counts': {},
                'processing_time_seconds': time.time() - start_time
            }

        # Save to JSON files
        output_dir = os.path.join(settings.BASE_DIR, "output", db_name)
        os.makedirs(output_dir, exist_ok=True)
        record_counts = {}

        for sub_entity_name, sub_entity_data in extracted_data.items():
            file_name = f"{sub_entity_name}.json"
            file_path = os.path.join(output_dir, file_name)

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(sub_entity_data, f, ensure_ascii=False, indent=4)

            record_count = len(sub_entity_data) if isinstance(sub_entity_data, list) else 1
            record_counts[sub_entity_name] = record_count
            logger.info(f"[ENTITY: {entity_name}] Saved {sub_entity_name} ({record_count} records)")

        processing_time = time.time() - start_time
        logger.info(f"[ENTITY: {entity_name}] ✓ Completed in {processing_time:.2f}s")

        return {
            'status': 'success',
            'entity_name': entity_name,
            'extracted_data': extracted_data,
            'record_counts': record_counts,
            'processing_time_seconds': processing_time
        }

    except Exception as e:
        processing_time = time.time() - start_time
        logger.exception(f"[ENTITY: {entity_name}] ✗ Failed: {e}")
        return {
            'status': 'error',
            'entity_name': entity_name,
            'error_message': str(e),
            'processing_time_seconds': processing_time
        }


@shared_task
def run_bulk_entity_task(
    okta_access_token=None,
    okta_granted_scopes=None,
    max_workers=4
):
    """
    Background task to fetch data from all Okta entities and store in MongoDB.
    Uses Celery's group() to spawn parallel tasks for each entity group.

    Args:
        okta_access_token: Optional OAuth access token from user session.
                          If provided, uses Bearer token authentication.
                          If None, falls back to SSWS API token.
        okta_granted_scopes: List of OAuth scopes granted to the access token.
        max_workers: Not used in Celery version (kept for API compatibility).
    """
    start_time = time.time()
    db_name = get_dynamic_db()
    total_groups = len(ENTITY_VIEWSETS)

    logger.info("=" * 80)
    logger.info(f"PARALLEL BULK FETCH STARTING (Celery Group)")
    logger.info(f"Entity Groups: {total_groups} | DB: {db_name}")
    logger.info("=" * 80)

    # Log authentication method being used
    if okta_access_token:
        logger.info("Using Bearer token authentication (user's OAuth token)")
        logger.info(f"Granted scopes: {okta_granted_scopes}")
    else:
        logger.info("Using SSWS token authentication (static API token fallback)")

    try:
        # Ensure MongoDB connection in main process (for initial setup)
        ensure_mongo_connection(db_name)
        logger.info(f"MongoDB connection established for db_name={db_name}")

        # Create parallel tasks using Celery's group
        # Each entity group gets its own task
        tasks = []
        for entity_name, viewset_class in ENTITY_VIEWSETS.items():
            # Get viewset class path for pickling
            viewset_class_path = f"{viewset_class.__module__}.{viewset_class.__name__}"

            # Create task signature
            task = process_single_entity_group.s(
                entity_name=entity_name,
                viewset_class_path=viewset_class_path,
                db_name=db_name,
                okta_access_token=okta_access_token,
                okta_granted_scopes=okta_granted_scopes
            )
            tasks.append(task)

        # Execute all tasks in parallel using Celery group
        logger.info(f"Spawning {len(tasks)} parallel Celery tasks...")
        job = group(tasks)
        result = job.apply_async()

        # Wait for all tasks to complete (with timeout)
        try:
            results = result.get(timeout=600)  # 10 minute timeout for all tasks
        except Exception as e:
            logger.error(f"Error waiting for results: {e}")
            results = []

        # Aggregate results
        successful = 0
        failed = 0
        error_details = []

        for res in results:
            if res.get('status') == 'success':
                successful += 1
                logger.info(f"✓ {res['entity_name']}: {res.get('processing_time_seconds', 0):.2f}s")
            else:
                failed += 1
                error_details.append({
                    'entity': res.get('entity_name', 'unknown'),
                    'error': res.get('error_message', 'Unknown error')
                })
                logger.error(f"✗ {res.get('entity_name', 'unknown')}: {res.get('error_message', 'Unknown error')}")

        # Determine overall status
        if failed == 0:
            overall_status = 'success'
            notify_status = 'completed'
        elif successful > 0:
            overall_status = 'partial_success'
            notify_status = 'partial_completed'
        else:
            overall_status = 'error'
            notify_status = 'failed'

        total_time = time.time() - start_time

        logger.info("=" * 80)
        logger.info(f"PARALLEL BULK FETCH COMPLETED")
        logger.info(f"Status: {overall_status} | Successful: {successful}/{total_groups} | Time: {total_time:.2f}s")
        logger.info("=" * 80)

        # Notify via RabbitMQ
        notify_backend_via_rabbitmq(db_name, notify_status, error_details if error_details else None)

        return {
            "status": overall_status,
            "db_name": db_name,
            "total_groups": total_groups,
            "successful_groups": successful,
            "failed_groups": failed,
            "total_time_seconds": total_time,
            "errors": error_details if error_details else None
        }

    except Exception as e:
        logger.exception(f"Error during bulk entity fetch for db {db_name}: {e}")
        notify_backend_via_rabbitmq(db_name, 'failed', [{'entity': 'main_task', 'error': str(e)}])
        return {"status": "error", "db_name": db_name, "error": str(e)}


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
