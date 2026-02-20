"""
Logging utility functions for BridgeSec.
Provides helper functions for logging common operations.
"""

import logging
import time
from functools import wraps

logger = logging.getLogger(__name__)


def log_okta_api_call(endpoint, method, status_code, duration_ms, rate_limit_remaining=None, request_id=None):
    """
    Log Okta API calls with standardized format.

    Args:
        endpoint: Okta API endpoint (e.g., '/api/v1/users')
        method: HTTP method (GET, POST, etc.)
        status_code: HTTP status code
        duration_ms: Request duration in milliseconds
        rate_limit_remaining: Remaining rate limit count
        request_id: Request tracing ID
    """
    log_level = logging.INFO if status_code < 400 else logging.WARNING

    extra = {
        'component': 'okta_api',
        'endpoint': endpoint,
        'method': method,
        'status_code': status_code,
        'duration_ms': duration_ms,
    }

    if request_id:
        extra['request_id'] = request_id
    if rate_limit_remaining is not None:
        extra['rate_limit_remaining'] = rate_limit_remaining

    message = f"Okta API call: {method} {endpoint} - {status_code} ({duration_ms}ms)"
    if rate_limit_remaining is not None:
        message += f" [Rate limit: {rate_limit_remaining}]"

    logger.log(log_level, message, extra=extra)


def log_task_start(task_name, params=None, request_id=None):
    """
    Log Celery task start.

    Args:
        task_name: Name of the task
        params: Task parameters (will be sanitized)
        request_id: Request tracing ID
    """
    extra = {
        'component': 'celery',
        'task_name': task_name,
        'task_status': 'started',
    }

    if request_id:
        extra['request_id'] = request_id
    if params:
        # Sanitize params (remove sensitive data)
        sanitized_params = _sanitize_params(params)
        extra['params'] = sanitized_params

    logger.info(f"Task started: {task_name}", extra=extra)


def log_task_complete(task_name, result=None, duration_ms=None, request_id=None):
    """
    Log Celery task completion.

    Args:
        task_name: Name of the task
        result: Task result summary
        duration_ms: Task duration in milliseconds
        request_id: Request tracing ID
    """
    extra = {
        'component': 'celery',
        'task_name': task_name,
        'task_status': 'completed',
    }

    if request_id:
        extra['request_id'] = request_id
    if duration_ms:
        extra['duration_ms'] = duration_ms
    if result:
        extra['result'] = result

    message = f"Task completed: {task_name}"
    if duration_ms:
        message += f" ({duration_ms}ms)"

    logger.info(message, extra=extra)


def log_task_error(task_name, error, duration_ms=None, request_id=None):
    """
    Log Celery task error.

    Args:
        task_name: Name of the task
        error: Error message or exception
        duration_ms: Task duration in milliseconds
        request_id: Request tracing ID
    """
    extra = {
        'component': 'celery',
        'task_name': task_name,
        'task_status': 'failed',
        'error': str(error),
    }

    if request_id:
        extra['request_id'] = request_id
    if duration_ms:
        extra['duration_ms'] = duration_ms

    logger.error(f"Task failed: {task_name} - {str(error)}", extra=extra)


def log_worker_assignment(worker_id, entity_group, request_id=None):
    """
    Log parallel worker assignment.

    Args:
        worker_id: Worker identifier (1-4)
        entity_group: Entity group assigned to worker
        request_id: Request tracing ID
    """
    extra = {
        'component': 'worker',
        'worker_id': worker_id,
        'entity_group': entity_group,
    }

    if request_id:
        extra['request_id'] = request_id

    logger.info(f"Worker {worker_id} assigned entity group: {entity_group}", extra=extra)


def log_mongodb_operation(operation, collection, count=None, duration_ms=None, request_id=None):
    """
    Log MongoDB operations.

    Args:
        operation: Operation type (insert, update, delete, find)
        collection: Collection name
        count: Number of documents affected
        duration_ms: Operation duration in milliseconds
        request_id: Request tracing ID
    """
    extra = {
        'component': 'mongodb',
        'operation': operation,
        'collection': collection,
    }

    if request_id:
        extra['request_id'] = request_id
    if count is not None:
        extra['count'] = count
    if duration_ms is not None:
        extra['duration_ms'] = duration_ms

    message = f"MongoDB {operation}: {collection}"
    if count is not None:
        message += f" ({count} documents)"
    if duration_ms is not None:
        message += f" in {duration_ms}ms"

    logger.info(message, extra=extra)


def log_restore_operation(entity_type, operation_type, count, request_id=None, user=None):
    """
    Log restore/create operations.

    Args:
        entity_type: Type of entity (policy_mfa, app_oauth, etc.)
        operation_type: restore or create
        count: Number of entities processed
        request_id: Request tracing ID
        user: Username performing the operation
    """
    extra = {
        'component': 'restore',
        'entity_type': entity_type,
        'operation_type': operation_type,
        'count': count,
    }

    if request_id:
        extra['request_id'] = request_id
    if user:
        extra['user'] = user

    logger.info(
        f"Restore operation: {operation_type} {count} {entity_type}",
        extra=extra
    )


def log_terraform_api_call(entity_type, operation, status_code, duration_ms=None, request_id=None):
    """
    Log Terraform API calls.

    Args:
        entity_type: Entity type being sent to Terraform
        operation: Operation type (apply, destroy)
        status_code: HTTP status code
        duration_ms: Request duration
        request_id: Request tracing ID
    """
    extra = {
        'component': 'terraform_api',
        'entity_type': entity_type,
        'event': operation,
        'operation':'Log Tf Api-Calls',
        'status_code': status_code,
    }

    if request_id:
        extra['request_id'] = request_id
    if duration_ms:
        extra['duration_ms'] = duration_ms

    log_level = logging.INFO if status_code < 400 else logging.WARNING

    logger.log(
        log_level,
        f"Terraform API call: {operation} {entity_type} - {status_code}",
        extra=extra
    )


def _sanitize_params(params):
    """
    Sanitize sensitive parameters before logging.
    """
    if isinstance(params, dict):
        sanitized = {}
        for key, value in params.items():
            if any(sensitive in key.lower() for sensitive in ['token', 'password', 'secret', 'key']):
                sanitized[key] = '***REDACTED***'
            elif isinstance(value, (dict, list)):
                sanitized[key] = _sanitize_params(value)
            else:
                sanitized[key] = value
        return sanitized
    elif isinstance(params, list):
        return [_sanitize_params(item) for item in params]
    else:
        return params


# Context manager for timing operations
class LogExecutionTime:
    """
    Context manager to log execution time of code blocks.

    Usage:
        with LogExecutionTime("fetch_users", logger, request_id="123"):
            # code to time
            fetch_users()
    """

    def __init__(self, operation_name, logger_instance=None, request_id=None, **extra_fields):
        self.operation_name = operation_name
        self.logger = logger_instance or logger
        self.request_id = request_id
        self.extra_fields = extra_fields
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = int((time.time() - self.start_time) * 1000)

        extra = {'duration_ms': duration_ms}
        if self.request_id:
            extra['request_id'] = self.request_id
        extra.update(self.extra_fields)

        if exc_type:
            self.logger.error(
                f"{self.operation_name} failed after {duration_ms}ms: {exc_val}",
                extra=extra,
                exc_info=True
            )
        else:
            self.logger.info(
                f"{self.operation_name} completed in {duration_ms}ms",
                extra=extra
            )


# ============================================================================
# Terraform-Specific Logging Functions (for OkTfModules)
# ============================================================================

def log_terraform_operation(operation, exit_code, duration_ms=None, resource_count=None, entity_type=None, request_id=None):
    """
    Log Terraform operations (init/plan/apply/destroy).

    Args:
        operation: Operation type (init, plan, apply, destroy)
        exit_code: Terraform command exit code
        duration_ms: Operation duration in milliseconds
        resource_count: Number of resources affected
        entity_type: Entity type being operated on
        request_id: Request tracing ID
    """
    log_level = logging.INFO if exit_code == 0 else logging.ERROR

    extra = {
        'component': 'terraform',
        'operation': operation,
        'exit_code': exit_code,
    }

    if request_id:
        extra['request_id'] = request_id
    if duration_ms is not None:
        extra['duration_ms'] = duration_ms
    if resource_count is not None:
        extra['resource_count'] = resource_count
    if entity_type:
        extra['entity_type'] = entity_type

    message = f"Terraform {operation}: exit_code={exit_code}"
    if resource_count is not None:
        message += f", resources={resource_count}"
    if duration_ms is not None:
        message += f", duration={duration_ms}ms"

    logger.log(log_level, message, extra=extra)


def log_terraform_plan(changes_add, changes_change, changes_destroy, entity_type=None, request_id=None):
    """
    Log Terraform plan results.

    Args:
        changes_add: Number of resources to add
        changes_change: Number of resources to change
        changes_destroy: Number of resources to destroy
        entity_type: Entity type being planned
        request_id: Request tracing ID
    """
    extra = {
        'component': 'terraform',
        'operation': 'Log Tf-Plan',
        'changes_add': changes_add,
        'changes_change': changes_change,
        'changes_destroy': changes_destroy,
        'resource_count': changes_add + changes_change + changes_destroy,
    }

    if request_id:
        extra['request_id'] = request_id
    if entity_type:
        extra['entity_type'] = entity_type

    logger.info(
        f"Terraform plan: +{changes_add} ~{changes_change} -{changes_destroy}",
        extra=extra
    )


def log_input_file_operation(entity_type, operation, file_path, record_count, request_id=None):
    """
    Log input JSON file operations.

    Args:
        entity_type: Entity type (okta_policy_mfa, okta_app_oauth, etc.)
        operation: Operation type (read, write, validate)
        file_path: Path to the input file
        record_count: Number of records in the file
        request_id: Request tracing ID
    """
    extra = {
        'component': 'input_file',
        'entity_type': entity_type,
        'operation': 'Log Json-File',
        'file_path': str(file_path),
        'resource_count': record_count,
    }

    if request_id:
        extra['request_id'] = request_id

    logger.info(
        f"Input file {operation}: {entity_type} ({record_count} records)",
        extra=extra
    )


def log_target_building(entity_type, target_count, targets, request_id=None):
    """
    Log Terraform target building.

    Args:
        entity_type: Entity type
        target_count: Number of targets built
        targets: List of target resource addresses
        request_id: Request tracing ID
    """
    extra = {
        'component': 'terraform',
        'operation': 'build_targets',
        'entity_type': entity_type,
        'resource_count': target_count,
        'targets': targets[:10] if len(targets) > 10 else targets,  # Log max 10 targets
    }

    if request_id:
        extra['request_id'] = request_id

    message = f"Built {target_count} Terraform targets for {entity_type}"
    if target_count > 10:
        message += f" (showing first 10)"

    logger.info(message, extra=extra)


def log_validation_result(entity_type, is_valid, error_count=0, errors=None, request_id=None):
    """
    Log data validation results.

    Args:
        entity_type: Entity type being validated
        is_valid: Whether validation passed
        error_count: Number of validation errors
        errors: List of validation error messages
        request_id: Request tracing ID
    """
    log_level = logging.INFO if is_valid else logging.WARNING

    extra = {
        'component': 'validation',
        'entity_type': entity_type,
        'is_valid': is_valid,
        'error_count': error_count,
        'operaion':'Log Data Validation',
    }

    if request_id:
        extra['request_id'] = request_id
    if errors and len(errors) <= 5:
        extra['errors'] = errors

    message = f"Validation {'passed' if is_valid else 'failed'} for {entity_type}"
    if error_count > 0:
        message += f" ({error_count} errors)"

    logger.log(log_level, message, extra=extra)
