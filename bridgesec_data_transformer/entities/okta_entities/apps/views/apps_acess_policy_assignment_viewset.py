import logging

from entities.okta_entities.apps.views.apps_base_viewset import BaseAppViewSet
from entities.okta_entities.apps.apps_models import AppAcessPolicyAssignment
from entities.okta_entities.apps.apps_serializers import AppAcessPolicyAssignmentSerializer

logger = logging.getLogger(__name__)


class AppAcessPolicyAssignmentViewSet(BaseAppViewSet):
    okta_endpoint = "/api/v1/apps"
    entity_type = "apps_access_policy_assignment"
    serializer_class = AppAcessPolicyAssignmentSerializer
    model = AppAcessPolicyAssignment

    def extract_data(self, okta_data):
        """
        Extract access policy info from apps.

        :param apps: list of app dicts from Okta
        :param mode: 'full' = fetch full access policy object,
        'id_only' = extract only the access policy ID
        :return: list of extracted dicts
        """
        formatted_data = []

        for app in okta_data:
            app_id = app.get("id")
            access_policy_url = app.get("_links", {}).get("accessPolicy", {}).get("href")

            if not access_policy_url:
                logger.info(f"No access policy found for app {app_id}. Skipping.")
                continue

            try:
                policy_id = access_policy_url.rstrip("/").split("/")[-1]
            except Exception as e:
                logger.error(f"Failed to extract policy ID from {access_policy_url}: {e}")
                continue


            formatted_record = {
                "app_id": app_id,
                "policy_id": policy_id,
            }
            formatted_data.append(formatted_record)

        logger.info("Final extracted %d policy assignment records", len(formatted_data))
        return formatted_data









