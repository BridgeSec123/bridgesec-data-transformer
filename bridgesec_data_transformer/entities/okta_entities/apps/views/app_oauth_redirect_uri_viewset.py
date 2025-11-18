import logging

from entities.okta_entities.apps.apps_models import AppOauthRedirectUri
from entities.okta_entities.apps.apps_serializers import (
    AppOauthRedirectUriSerializer,
)
from entities.okta_entities.apps.views.apps_base_viewset import BaseAppViewSet

logger = logging.getLogger(__name__)

class AppOauthRedirectUriViewSet(BaseAppViewSet):
    """
    ViewSet for extracting OAuth redirect URIs from OAuth apps.
    This entity relies on okta_app_oauth as parent and does not make separate Okta API calls.
    """
    entity_type = "okta_apps_oauth_redirect_uri"
    serializer_class = AppOauthRedirectUriSerializer
    model = AppOauthRedirectUri

    def extract_data(self, okta_data, parent_record=None):
        """
        Extract redirect URIs from the parent okta_app_oauth data.

        Args:
            okta_data: List containing the parent OAuth app record
            parent_record: The OAuth app record from okta_app_oauth collection

        Returns:
            List of formatted redirect URI records
        """
        logger.info("Starting extraction of OAuth redirect URIs from parent okta_app_oauth data")

        if not parent_record:
            logger.warning("No parent record provided for redirect URI extraction")
            return []

        formatted_data = []

        # Extract redirect URIs from the parent OAuth app record
        app_id = parent_record.get("app_id")
        app_label = parent_record.get("label")
        redirect_uris = parent_record.get("redirect_uris", [])

        logger.info(f"Processing OAuth app: app_id={app_id}, label={app_label}, redirect_uris={redirect_uris}")

        if not app_id:
            logger.warning(f"Missing app_id in parent OAuth app record for label: {app_label}. Skipping.")
            return []

        if not redirect_uris or len(redirect_uris) == 0:
            logger.info(f"No redirect URIs found for app_id: {app_id} (label: {app_label}). Skipping.")
            return []

        # Create a record for this app with its redirect URIs
        formatted_record = {
            "app_id": app_id,  # Store the actual app_id from parent OAuth app
            "uri": redirect_uris
        }
        formatted_data.append(formatted_record)
        logger.info(f"✓ Extracted {len(redirect_uris)} redirect URI(s) for app_id: {app_id} (label: {app_label})")

        logger.info("Completed extraction of %d OAuth redirect URI record(s)", len(formatted_data))
        return formatted_data
