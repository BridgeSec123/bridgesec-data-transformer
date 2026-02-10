"""
Decorators for automatic logging of function execution.
"""

import logging
import time
from functools import wraps

logger = logging.getLogger(__name__)


def log_execution_time(func):
    """
    Decorator to automatically log function execution time.

    Usage:
        @log_execution_time
        def my_function():
            # function code
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        func_name = f"{func.__module__}.{func.__name__}"

        # Extract request_id if present in kwargs
        request_id = kwargs.get('request_id')

        try:
            result = func(*args, **kwargs)
            duration_ms = int((time.time() - start_time) * 1000)

            extra = {
                'function': func_name,
                'duration_ms': duration_ms,
            }
            if request_id:
                extra['request_id'] = request_id

            logger.info(
                f"{func_name} executed in {duration_ms}ms",
                extra=extra
            )
            return result

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)

            extra = {
                'function': func_name,
                'duration_ms': duration_ms,
                'error': str(e),
            }
            if request_id:
                extra['request_id'] = request_id

            logger.error(
                f"{func_name} failed after {duration_ms}ms: {str(e)}",
                extra=extra,
                exc_info=True
            )
            raise

    return wrapper


def log_errors(func):
    """
    Decorator to automatically log exceptions with context.

    Usage:
        @log_errors
        def risky_function():
            # function code that might fail
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        func_name = f"{func.__module__}.{func.__name__}"
        request_id = kwargs.get('request_id')

        try:
            return func(*args, **kwargs)
        except Exception as e:
            extra = {
                'function': func_name,
                'error_type': type(e).__name__,
                'error': str(e),
            }
            if request_id:
                extra['request_id'] = request_id

            logger.exception(
                f"Exception in {func_name}: {str(e)}",
                extra=extra
            )
            raise

    return wrapper


def log_okta_request(func):
    """
    Decorator to log Okta API requests.

    Usage:
        @log_okta_request
        def make_okta_call(endpoint, method, ...):
            # Okta API call
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        endpoint = kwargs.get('endpoint', args[0] if args else 'unknown')
        method = kwargs.get('method', args[1] if len(args) > 1 else 'GET')
        request_id = kwargs.get('request_id')

        try:
            result = func(*args, **kwargs)
            duration_ms = int((time.time() - start_time) * 1000)

            # Try to extract status code from result
            status_code = getattr(result, 'status_code', 200)
            rate_limit = None
            if hasattr(result, 'headers'):
                rate_limit = result.headers.get('X-Rate-Limit-Remaining')

            extra = {
                'component': 'okta_api',
                'endpoint': endpoint,
                'method': method,
                'status_code': status_code,
                'duration_ms': duration_ms,
            }
            if request_id:
                extra['request_id'] = request_id
            if rate_limit:
                extra['rate_limit_remaining'] = rate_limit

            log_level = logging.INFO if status_code < 400 else logging.WARNING

            logger.log(
                log_level,
                f"Okta API: {method} {endpoint} - {status_code} ({duration_ms}ms)",
                extra=extra
            )

            return result

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)

            extra = {
                'component': 'okta_api',
                'endpoint': endpoint,
                'method': method,
                'duration_ms': duration_ms,
                'error': str(e),
            }
            if request_id:
                extra['request_id'] = request_id

            logger.error(
                f"Okta API failed: {method} {endpoint} - {str(e)}",
                extra=extra,
                exc_info=True
            )
            raise

    return wrapper
