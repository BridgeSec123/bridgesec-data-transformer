import logging

from core.utils.okta_helpers import get_permissions

from entities.okta_entities.administrators.views.administrators_base_viewset import BaseAdministratorViewSet
from entities.okta_entities.administrators.administrators_models import AdminResourseset
from entities.okta_entities.administrators.administrators_serializers import AdminResoursesetSerializer

logger = logging.getLogger(__name__)

class AdminResourcesetViewSet(BaseAdministratorViewSet):
    okta_endpoint = "/api/v1/iam/resource-sets"
    entity_type = "okta_resource_set"
    serializer_class = AdminResoursesetSerializer
    model = AdminResourseset

    def extract_data(self, okta_data):
        """
        Override to format the user data by removing the "profile" key.
        """
        logger.info("Extracting data from Okta response")
        formatted_data = []
        for record in okta_data.get("resource-sets", []):
            label = record.get("label", "")
            description = record.get("description", "")
            resources = record.get("_links", {}).get("resources", {}).get("href", "")

            formatted_data.append(
                {
                    "label": label,
                    "description": description,
                    "resources": [resources]
                }
            )
        logger.info("Extracted and formatted %d user records from Okta", len(formatted_data))

        return formatted_data