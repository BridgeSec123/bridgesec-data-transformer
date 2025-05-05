import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

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