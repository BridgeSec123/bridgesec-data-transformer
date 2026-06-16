"""
Parallel execution utilities for bulk entity processing.

This module provides process-based parallelism for fetching Okta entities,
with proper handling of MongoDB connections and error isolation.
"""

import json
import logging
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime

from django.conf import settings

logger = logging.getLogger(__name__)


@dataclass
class EntityGroupResult:
    """Result of processing a single entity group."""
    entity_name: str
    status: str  # 'success' or 'error'
    extracted_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    processing_time_seconds: float = 0.0
    record_counts: Optional[Dict[str, int]] = None


@dataclass
class ParallelExecutionResult:
    """Aggregated result of parallel execution."""
    db_name: str
    status: str  # 'success', 'partial_success', or 'error'
    total_groups: int
    successful_groups: int
    failed_groups: int
    results: List[EntityGroupResult]
    total_time_seconds: float


def _init_worker_process(db_name: str, mongo_uri: str = None):
    """
    Initialize a worker process with fresh MongoDB connections.

    This function is called once when each worker process starts.
    It ensures clean connection state for multiprocessing safety.
    """
    # Import here to avoid issues with module loading in forked processes
    from core.utils.mongo_utils import reset_connections_for_process, ensure_mongo_connection

    # Reset any inherited connection state
    reset_connections_for_process()

    # Establish fresh connections for this worker using tenant URI when available
    ensure_mongo_connection(db_name, mongo_uri=mongo_uri)

    logger.info(f"[PID {os.getpid()}] Worker initialized for database: {db_name}")


def process_entity_group(
    entity_name: str,
    viewset_class_path: str,  # Fully qualified class path for pickling
    db_name: str,
    okta_access_token: Optional[str],
    okta_granted_scopes: Optional[List[str]],
    output_dir: str,
    mongo_uri: Optional[str] = None,
) -> EntityGroupResult:
    """
    Process a single entity group in a worker process.

    This function is the main work unit for parallel execution.
    It fetches data from Okta, stores in MongoDB, and saves to JSON.

    Args:
        entity_name: Name of the entity group (e.g., 'users', 'groups')
        viewset_class_path: Full module path to viewset class
        db_name: Target MongoDB database name
        okta_access_token: OAuth access token (optional)
        okta_granted_scopes: List of granted OAuth scopes
        output_dir: Directory for JSON output files

    Returns:
        EntityGroupResult with status and data
    """
    import time
    start_time = time.time()
    pid = os.getpid()

    # Log immediately to confirm worker is called
    print(f"[WORKER PID {pid}] CALLED for entity: {entity_name}", flush=True)
    logger.info(f"[WORKER PID {pid}] CALLED for entity: {entity_name}")

    try:
        logger.info(f"[PID {pid}] Starting entity group: {entity_name}")
        logger.info(f"[PID {pid}] Viewset class path: {viewset_class_path}")

        # Import dependencies inside worker to ensure fresh module state
        from core.utils.mongo_utils import ensure_mongo_connection
        from importlib import import_module

        # Ensure MongoDB connection for this worker using tenant URI when available
        ensure_mongo_connection(db_name, mongo_uri=mongo_uri)

        # Dynamically import viewset class from path
        module_path, class_name = viewset_class_path.rsplit('.', 1)
        module = import_module(module_path)
        viewset_class = getattr(module, class_name)

        # Create mock request for OAuth token passing
        mock_request = None
        if okta_access_token:
            from core.tasks.bulk_tasks import MockRequest
            mock_request = MockRequest(okta_access_token, okta_granted_scopes)

        # Instantiate viewset and fetch data
        viewset_instance = viewset_class()
        extracted_data = viewset_instance.fetch_and_store_data(db_name, request=mock_request)

        if not extracted_data:
            logger.warning(f"[PID {pid}] No data extracted for {entity_name}")
            return EntityGroupResult(
                entity_name=entity_name,
                status='success',
                extracted_data={},
                record_counts={},
                processing_time_seconds=time.time() - start_time
            )

        # Save data to JSON files (thread-safe with unique file paths)
        os.makedirs(output_dir, exist_ok=True)
        record_counts = {}

        for sub_entity_name, sub_entity_data in extracted_data.items():
            file_name = f"{sub_entity_name}.json"
            file_path = os.path.join(output_dir, file_name)

            # Atomic write with temp file to avoid partial writes
            temp_file_path = f"{file_path}.{pid}.tmp"
            try:
                with open(temp_file_path, "w", encoding="utf-8") as f:
                    json.dump(sub_entity_data, f, ensure_ascii=False, indent=4)

                # Atomic rename (works on Windows and Unix)
                if os.path.exists(file_path):
                    os.remove(file_path)
                os.rename(temp_file_path, file_path)

                record_count = len(sub_entity_data) if isinstance(sub_entity_data, list) else 1
                record_counts[sub_entity_name] = record_count
                logger.info(f"[PID {pid}] Saved {sub_entity_name} ({record_count} records) to {file_path}")

            except Exception as e:
                logger.exception(f"[PID {pid}] Error saving {sub_entity_name}: {e}")
                # Clean up temp file if it exists
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)

        processing_time = time.time() - start_time
        logger.info(f"[PID {pid}] Completed {entity_name} in {processing_time:.2f}s")

        return EntityGroupResult(
            entity_name=entity_name,
            status='success',
            extracted_data=extracted_data,
            record_counts=record_counts,
            processing_time_seconds=processing_time
        )

    except Exception as e:
        processing_time = time.time() - start_time
        logger.exception(f"[PID {pid}] Error processing {entity_name}: {e}")
        return EntityGroupResult(
            entity_name=entity_name,
            status='error',
            error_message=str(e),
            processing_time_seconds=processing_time
        )


def get_viewset_class_path(viewset_class) -> str:
    """
    Get the fully qualified class path for a viewset class.
    Required for pickling when passing to worker processes.
    """
    return f"{viewset_class.__module__}.{viewset_class.__name__}"


def execute_parallel_bulk_fetch(
    entity_viewsets: Dict[str, Any],
    db_name: str,
    okta_access_token: Optional[str] = None,
    okta_granted_scopes: Optional[List[str]] = None,
    max_workers: int = 4,
    mongo_uri: Optional[str] = None,
) -> ParallelExecutionResult:
    """
    Execute bulk entity fetch in parallel using ProcessPoolExecutor.

    Args:
        entity_viewsets: Dictionary of entity_name -> viewset_class
        db_name: Target MongoDB database name
        okta_access_token: OAuth access token (optional)
        okta_granted_scopes: List of granted OAuth scopes
        max_workers: Number of parallel worker processes (default: 4)

    Returns:
        ParallelExecutionResult with aggregated results
    """
    import time
    start_time = time.time()

    output_dir = os.path.join(settings.BASE_DIR, "output", db_name)
    os.makedirs(output_dir, exist_ok=True)

    results: List[EntityGroupResult] = []
    total_groups = len(entity_viewsets)

    logger.info("=" * 80)
    logger.info(f"PARALLEL BULK FETCH STARTING")
    logger.info(f"Workers: {max_workers} | Entity Groups: {total_groups} | DB: {db_name}")
    logger.info("=" * 80)

    # Prepare task arguments
    tasks = []
    for entity_name, viewset_class in entity_viewsets.items():
        viewset_class_path = get_viewset_class_path(viewset_class)
        tasks.append((
            entity_name,
            viewset_class_path,
            db_name,
            okta_access_token,
            okta_granted_scopes,
            output_dir,
            mongo_uri,
        ))

    # Execute in parallel with ProcessPoolExecutor
    # Explicitly use 'spawn' context for Windows/Docker compatibility
    import multiprocessing
    ctx = multiprocessing.get_context('spawn')

    try:
        executor = ProcessPoolExecutor(
            max_workers=max_workers,
            mp_context=ctx,
            initializer=_init_worker_process,
            initargs=(db_name, mongo_uri),
        )
    except Exception as e:
        logger.error(f"Failed to create ProcessPoolExecutor: {e}")
        logger.info("Falling back to sequential execution")
        # Fallback to sequential processing
        for task_args in tasks:
            result = process_entity_group(*task_args)
            results.append(result)

        successful = sum(1 for r in results if r.status == 'success')
        failed = sum(1 for r in results if r.status == 'error')
        overall_status = 'success' if failed == 0 else 'partial_success' if successful > 0 else 'error'

        return ParallelExecutionResult(
            db_name=db_name,
            status=overall_status,
            total_groups=total_groups,
            successful_groups=successful,
            failed_groups=failed,
            results=results,
            total_time_seconds=time.time() - start_time
        )

    with executor:
        # Submit all tasks
        future_to_entity = {
            executor.submit(process_entity_group, *task_args): task_args[0]
            for task_args in tasks
        }

        # Collect results as they complete
        for future in as_completed(future_to_entity):
            entity_name = future_to_entity[future]
            try:
                result = future.result(timeout=300)  # 5 minute timeout per group
                results.append(result)
                if result.status == 'success':
                    logger.info(f"✓ Completed: {entity_name} [{result.status}] - {result.processing_time_seconds:.2f}s")
                else:
                    logger.error(f"✗ Failed: {entity_name} [{result.status}] - {result.error_message}")
            except TimeoutError as e:
                logger.exception(f"TIMEOUT for {entity_name}: Exceeded 5 minutes")
                results.append(EntityGroupResult(
                    entity_name=entity_name,
                    status='error',
                    error_message=f"Timeout: {str(e)}"
                ))
            except Exception as e:
                logger.exception(f"EXCEPTION for {entity_name}: {e}")
                import traceback
                full_error = traceback.format_exc()
                logger.error(f"Full traceback:\n{full_error}")
                results.append(EntityGroupResult(
                    entity_name=entity_name,
                    status='error',
                    error_message=str(e)
                ))

    # Aggregate results
    successful = sum(1 for r in results if r.status == 'success')
    failed = sum(1 for r in results if r.status == 'error')

    if failed == 0:
        overall_status = 'success'
    elif successful > 0:
        overall_status = 'partial_success'
    else:
        overall_status = 'error'

    total_time = time.time() - start_time

    logger.info(
        f"Parallel bulk fetch completed: {successful}/{total_groups} succeeded, "
        f"{failed} failed, total time: {total_time:.2f}s"
    )

    return ParallelExecutionResult(
        db_name=db_name,
        status=overall_status,
        total_groups=total_groups,
        successful_groups=successful,
        failed_groups=failed,
        results=results,
        total_time_seconds=total_time
    )
