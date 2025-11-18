import logging

from entities.okta_entities.apps.apps_models import AppOauthPostRedirectUri
from entities.okta_entities.apps.apps_serializers import \
    AppOauthPostRedirectUriSerializer
from entities.okta_entities.apps.views.apps_base_viewset import BaseAppViewSet

logger = logging.getLogger(__name__)

class AppOauthPostRedirectUriViewSet(BaseAppViewSet):
    entity_type = "okta_apps_oauth_post_redirect_uri"
    serializer_class = AppOauthPostRedirectUriSerializer
    model = AppOauthPostRedirectUri

    def extract_data(self, okta_data, parent_record=None):
        """
        Extract post logout redirect URIs from the parent okta_app_oauth data.

        Args:
            okta_data: List containing the parent OAuth app record
            parent_record: The OAuth app record from okta_app_oauth collection

        Returns:
            List of formatted post logout redirect URI records
        """
        if not parent_record:
            logger.warning("No parent record provided for post logout redirect URI extraction")
            return []

        formatted_data = []

        # Extract post logout redirect URIs from the parent OAuth app record
        app_id = parent_record.get("app_id")
        app_label = parent_record.get("label")
        post_logout_redirect_uris = parent_record.get("post_logout_redirect_uris", [])

        logger.info(f"Processing OAuth app: app_id={app_id}, label={app_label}, post_logout_redirect_uris={post_logout_redirect_uris}")

        if not app_id:
            logger.warning(f"Missing app_id in parent OAuth app record for label: {app_label}. Skipping.")
            return []

        if not post_logout_redirect_uris or len(post_logout_redirect_uris) == 0:
            logger.info(f"No post logout redirect URIs found for app_id: {app_id} (label: {app_label}). Skipping.")
            return []

        # Create a record for this app with its post logout redirect URIs
        formatted_record = {
            "app_id": app_id,  # Store the actual app_id from parent OAuth app
            "uri": post_logout_redirect_uris
        }
        formatted_data.append(formatted_record)
        logger.info(f"✓ Extracted {len(post_logout_redirect_uris)} post logout redirect URI(s) for app_id: {app_id} (label: {app_label})")

        return formatted_data
