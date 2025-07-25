import logging

from entities.okta_entities.administrators.administrators_models import AdminResourceSet
from entities.okta_entities.administrators.administrators_serializers import (
    AdminResourceSetSerializer,
)
from entities.okta_entities.administrators.views.administrators_base_viewset import (
    BaseAdministratorViewSet,
)

logger = logging.getLogger(__name__)

class AdminResourceSetViewSet(BaseAdministratorViewSet):
    okta_endpoint = "/api/v1/iam/resource-sets"
    entity_type = "okta_resource_set"
    serializer_class = AdminResourceSetSerializer
    model = AdminResourceSet

    def extract_data(self, okta_data):
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
        logger.info("Extracted and formatted %d admin resource set records from Okta", len(formatted_data))
        return formatted_data