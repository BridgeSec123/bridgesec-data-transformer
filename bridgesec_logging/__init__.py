"""
BridgeSec Logging Package
Centralized structured logging for BridgeSec microservices.

This package provides:
- Structured JSON logging with Loki integration
- Request tracing with request_id propagation
- Automatic request/response logging middleware
- Utility functions for common logging operations
- Decorators for automatic function logging
"""

__version__ = "1.0.0"

# Configuration
from .config import setup_logging, get_logger, ContextFilter

# Middleware

from .middleware import LoggingMiddleware

# Utility functions
from .utils import (
    # BridgeSec-specific
    log_okta_api_call,
    log_task_start,
    log_task_complete,
    log_task_error,
    log_worker_assignment,
    log_mongodb_operation,
    log_restore_operation,
    log_terraform_api_call,

    # Terraform-specific (for OkTfModules)
    log_terraform_operation,
    log_terraform_plan,
    log_input_file_operation,
    log_target_building,
    log_validation_result,

    # Context manager
    LogExecutionTime,
)

# Decorators
from .decorators import (
    log_execution_time,
    log_errors,
    log_okta_request,
)

__all__ = [
    # Version
    '__version__',

    # Configuration
    'setup_logging',
    'get_logger',
    'ContextFilter',

    # Middleware
    'LoggingMiddleware',

    # Utility functions - BridgeSec
    'log_okta_api_call',
    'log_task_start',
    'log_task_complete',
    'log_task_error',
    'log_worker_assignment',
    'log_mongodb_operation',
    'log_restore_operation',
    'log_terraform_api_call',

    # Utility functions - Terraform
    'log_terraform_operation',
    'log_terraform_plan',
    'log_input_file_operation',
    'log_target_building',
    'log_validation_result',

    # Context manager
    'LogExecutionTime',

    # Decorators
    'log_execution_time',
    'log_errors',
    'log_okta_request',
]
