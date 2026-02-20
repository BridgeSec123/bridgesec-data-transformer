import logging
import time

import requests
from django.conf import settings
from bridgesec_logging import log_okta_api_call

logger = logging.getLogger(__name__)


def build_okta_url(endpoint):
    """
    Build a properly formatted Okta API URL.
    Handles trailing/leading slashes to avoid double slashes.

    Args:
        endpoint: The API endpoint (e.g., '/api/v1/users' or 'api/v1/users')

    Returns:
        str: Properly formatted URL
    """
    base_url = settings.OKTA_API_URL.rstrip('/')
    endpoint = endpoint.lstrip('/')
    return f"{base_url}/{endpoint}"


class OktaScopeError(Exception):
    """Exception raised when required Okta scope is missing."""

    def __init__(self, required_scope, endpoint):
        self.required_scope = required_scope
        self.endpoint = endpoint
        self.message = (
            f"Missing required Okta scope '{required_scope}' to access '{endpoint}'. "
            f"Please ensure the scope is granted in Okta Admin Console → Applications → Your App → Okta API Scopes."
        )
        super().__init__(self.message)


def get_required_scope_for_endpoint(endpoint):
    """
    Get the required Okta scope(s) for a given API endpoint.

    Args:
        endpoint: The Okta API endpoint path

    Returns:
        list: List of required scopes, or empty list if not found
    """
    scope_map = getattr(settings, 'OKTA_API_SCOPE_MAP', {})

    for path_pattern, scope in scope_map.items():
        if path_pattern in endpoint:
            # Handle both single scope (string) and multiple scopes (list)
            if isinstance(scope, list):
                return scope
            else:
                return [scope] if scope else []

    return []


def validate_scope_for_endpoint(request, endpoint):
    """
    Validate that the user has the required scope(s) for an endpoint.

    Args:
        request: Django request object
        endpoint: The Okta API endpoint being accessed

    Returns:
        tuple: (is_valid, required_scopes, granted_scopes, missing_scopes)
    """
    required_scopes = get_required_scope_for_endpoint(endpoint)

    if not required_scopes:
        # No specific scope required, allow access
        return True, [], [], []

    granted_scopes = []
    if request and hasattr(request, 'session'):
        granted_scopes = request.session.get('okta_granted_scopes', [])

    # Check which required scopes are missing
    missing_scopes = [scope for scope in required_scopes if scope not in granted_scopes]
    is_valid = len(missing_scopes) == 0

    return is_valid, required_scopes, granted_scopes, missing_scopes


def get_okta_headers(request=None):
    """
    Get authorization headers for Okta API calls.

    Uses OAuth access token from user's session (Bearer token).
    Falls back to static OKTA_API_TOKEN only if available and no session token.

    Args:
        request: Optional Django request object

    Returns:
        dict: Headers with Authorization
    """
    okta_access_token = None

    # Try to get Okta access token from session
    if request and hasattr(request, 'session'):
        okta_access_token = request.session.get('okta_access_token')

    if okta_access_token:
        # Use user's Okta access token (Bearer format)
        return {"Authorization": f"Bearer {okta_access_token}"}
    elif settings.OKTA_API_TOKEN:
        # Fallback to static API token only if configured (SSWS format)
        return {"Authorization": f"SSWS {settings.OKTA_API_TOKEN}"}
    else:
        # No token available
        logger.error("No Okta authentication token available! User must be logged in.",extra={"operation":"Get Okta Headers"})
        return {}


def make_okta_request(url, request=None, method="GET", data=None, params=None):
    """
    Make an authenticated request to Okta API with scope validation and error handling.

    Args:
        url: The Okta API URL
        request: Django request object (for session-based auth)
        method: HTTP method (GET, POST, etc.)
        data: Request body data
        params: Query parameters

    Returns:
        tuple: (response_data, error_info)
               error_info is None on success, or dict with error details on failure
    """
    # Get request_id from request if available
    request_id = getattr(request, 'request_id', None) if request else None

    headers = get_okta_headers(request)

    # Validate scope before making request
    is_valid, required_scopes, granted_scopes, missing_scopes = validate_scope_for_endpoint(request, url)

    # Log scope validation if missing scopes
    if missing_scopes:
        logger.warning(
            f"Okta API scope validation failed: {url}",
            extra={
                'component': 'okta_api',
                'request_id': request_id,
                'endpoint': url,
                'required_scopes': required_scopes,
                'granted_scopes': granted_scopes,
                'missing_scopes': missing_scopes,
            }
        )

    # Start timing the request
    start_time = time.time()

    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, params=params)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=data, params=params)
        elif method.upper() == "PUT":
            response = requests.put(url, headers=headers, json=data, params=params)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers, params=params)
        else:
            return None, {"error": f"Unsupported HTTP method: {method}"}

        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)

        # Extract rate limit info from headers
        rate_limit_remaining = response.headers.get('X-Rate-Limit-Remaining')
        rate_limit_limit = response.headers.get('X-Rate-Limit-Limit')
        rate_limit_reset = response.headers.get('X-Rate-Limit-Reset')

        # Log the Okta API call
        log_okta_api_call(
            endpoint=url,
            method=method,
            status_code=response.status_code,
            duration_ms=duration_ms,
            rate_limit_remaining=int(rate_limit_remaining) if rate_limit_remaining else None,
            request_id=request_id
        )

        # Warn if rate limit is low
        if rate_limit_remaining and int(rate_limit_remaining) < 100:
            logger.warning(
                f"Okta rate limit low: {rate_limit_remaining} remaining",
                extra={
                    'component': 'okta_api',
                    'request_id': request_id,
                    'endpoint': url,
                    'rate_limit_remaining': int(rate_limit_remaining),
                    'rate_limit_limit': int(rate_limit_limit) if rate_limit_limit else None,
                    'rate_limit_reset': rate_limit_reset,
                }
            )

        # Handle 401/403 errors with helpful scope message
        if response.status_code in [401, 403]:
            error_data = response.json() if response.content else {}
            error_code = error_data.get("errorCode", "")
            error_summary = error_data.get("errorSummary", "Access denied")

            # Check if it's a scope-related error
            scope_hint = ""
            if missing_scopes:
                scope_hint = (
                    f" Missing scopes: {missing_scopes}. "
                    f"Please grant these scopes in Okta Admin Console → Applications → Your App → Okta API Scopes."
                )

            error_info = {
                "error": "okta_api_access_denied",
                "status_code": response.status_code,
                "error_code": error_code,
                "error_summary": error_summary,
                "required_scopes": required_scopes,
                "missing_scopes": missing_scopes,
                "message": f"Access denied to Okta API: {error_summary}.{scope_hint}",
                "url": url
            }

            duration_ms = int((time.time() - start_time) * 1000)

            logger.error(
                f"Okta API access denied: {url}",
                extra={
                    'component': 'okta_api',
                    'request_id': request_id,
                    'endpoint': url,
                    'method': method,
                    'status_code': response.status_code,
                    'duration_ms': duration_ms,
                    'error_code': error_code,
                    'error_summary': error_summary,
                    'missing_scopes': missing_scopes,
                }
            )
            return None, error_info

        response.raise_for_status()
        return response.json() if response.content else {}, None

    except requests.exceptions.HTTPError as e:
        error_info = {
            "error": "okta_api_http_error",
            "status_code": e.response.status_code if e.response else None,
            "message": str(e),
            "url": url
        }
        logger.error(f"Okta API HTTP error: {error_info}")
        return None, error_info

    except requests.exceptions.RequestException as e:
        error_info = {
            "error": "okta_api_request_error",
            "message": str(e),
            "url": url
        }
        logger.error(f"Okta API request error: {error_info}")
        return None, error_info

def get_permissions(permissions_url, request=None):
        """
        Fetch permissions from the given URL.
        """
        try:
            headers = get_okta_headers(request)
            response = requests.get(permissions_url, headers=headers)
            response.raise_for_status()
            data = response.json()
            response_data = []
            for permission in data.get("permissions", []):
                response_data.append(permission.get("label"))
            return response_data

        except requests.exceptions.RequestException as e:
            logger.error("Failed to fetch permissions: %s", e)
            return []