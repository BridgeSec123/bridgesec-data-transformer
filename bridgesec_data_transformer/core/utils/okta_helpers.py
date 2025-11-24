import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def get_okta_headers(request=None):
    """
    Get authorization headers for Okta API calls.

    If request is provided and has a session with okta_access_token, uses that.
    Otherwise, falls back to static OKTA_API_TOKEN from settings.

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
        logger.info("Using user's Okta access token from session")
        return {"Authorization": f"Bearer {okta_access_token}"}
    else:
        # Fallback to static API token (SSWS format)
        logger.info("Using static OKTA_API_TOKEN")
        return {"Authorization": f"SSWS {settings.OKTA_API_TOKEN}"}

def get_permissions(permissions_url):
        """
        Fetch permissions from the given URL.
        """
        try:
            headers = {"Authorization": f"SSWS {settings.OKTA_API_TOKEN}"}
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