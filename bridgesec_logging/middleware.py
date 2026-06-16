"""
Django middleware for automatic request/response logging.
Generates request_id for tracing and logs all HTTP requests.
"""

import logging
import time
import uuid
import json
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class LoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log all incoming HTTP requests and outgoing responses.
    Automatically generates a unique request_id for tracing.
    """

    # Sensitive fields to sanitize in logs
    SENSITIVE_FIELDS = [
        'password', 'token', 'api_key', 'secret', 'authorization',
        'access_token', 'refresh_token', 'ssws', 'bearer'
    ]

    def process_request(self, request):
        """
        Process incoming request - generate request_id and log details.
        """
        # Reset tenant context — authentication hasn't run yet at this point
        try:
            from core.utils.tenant_utils import set_current_tenant
            set_current_tenant(None)
        except Exception:
            pass

        # Generate unique request ID
        request.request_id = str(uuid.uuid4())
        request.start_time = time.time()

        # Extract user information
        user = 'anonymous'
        if hasattr(request, 'user') and request.user.is_authenticated:
            user = getattr(request.user, 'username', str(request.user))

        # Log request start
        logger.info(
            f"Request started: {request.method} {request.path}",
            extra={
                'request_id': request.request_id,
                'user': user,
                'component': 'api',
                'method': request.method,
                'path': request.path,
                'query_params': dict(request.GET),
                'remote_addr': self._get_client_ip(request),
                'tenant_id': 'unknown',
            }
        )

    def process_response(self, request, response):
        """
        Process outgoing response - log completion with duration.
        """
        # Calculate request duration
        duration_ms = 0
        if hasattr(request, 'start_time'):
            duration_ms = int((time.time() - request.start_time) * 1000)

        # Extract user
        user = 'anonymous'
        if hasattr(request, 'user') and request.user.is_authenticated:
            user = getattr(request.user, 'username', str(request.user))

        # Get request_id
        request_id = getattr(request, 'request_id', 'N/A')

        # Determine log level based on status code
        if response.status_code >= 500:
            log_level = logging.ERROR
        elif response.status_code >= 400:
            log_level = logging.WARNING
        else:
            log_level = logging.INFO

        # Log response
        _tenant = getattr(request, '_tenant', None)
        logger.log(
            log_level,
            f"Request completed: {request.method} {request.path} - {response.status_code} ({duration_ms}ms)",
            extra={
                'request_id': request_id,
                'user': user,
                'component': 'api',
                'method': request.method,
                'path': request.path,
                'status_code': response.status_code,
                'duration_ms': duration_ms,
                'tenant_id': str(_tenant.id) if _tenant else 'unknown',
            }
        )

        # Add request_id to response headers for tracing
        response['X-Request-ID'] = request_id

        return response

    def process_exception(self, request, exception):
        """
        Process exceptions - log with full traceback.
        """
        request_id = getattr(request, 'request_id', 'N/A')
        user = 'anonymous'
        if hasattr(request, 'user') and request.user.is_authenticated:
            user = getattr(request.user, 'username', str(request.user))

        _tenant = getattr(request, '_tenant', None)
        logger.exception(
            f"Request exception: {request.method} {request.path} - {str(exception)}",
            extra={
                'request_id': request_id,
                'user': user,
                'component': 'api',
                'method': request.method,
                'path': request.path,
                'exception_type': type(exception).__name__,
                'tenant_id': str(_tenant.id) if _tenant else 'unknown',
            }
        )

    def _get_client_ip(self, request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def _sanitize_data(self, data):
        """
        Sanitize sensitive data from logs.
        Replace sensitive field values with '***REDACTED***'.
        """
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                if any(sensitive in key.lower() for sensitive in self.SENSITIVE_FIELDS):
                    sanitized[key] = '***REDACTED***'
                elif isinstance(value, (dict, list)):
                    sanitized[key] = self._sanitize_data(value)
                else:
                    sanitized[key] = value
            return sanitized
        elif isinstance(data, list):
            return [self._sanitize_data(item) for item in data]
        else:
            return data
