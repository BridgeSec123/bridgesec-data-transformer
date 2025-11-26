import logging

import requests
from core.utils.okta_helpers import get_okta_headers
from django.conf import settings
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

    def get_resource_details(self, resources_url, request=None):
        """
        Fetch resource details from the resources URL and extract type and name.
        """
        if not resources_url:
            return []

        try:
            headers = get_okta_headers(request)
            response = requests.get(resources_url, headers=headers)

            if response.status_code == 200:
                resources_data = response.json()
                logger.info(f"Resources API response: {resources_data}")
                resource_objects = []

                # Check different possible response structures
                resources_list = (resources_data.get("resources", []) or
                                resources_data if isinstance(resources_data, list) else [])

                for resource in resources_list:
                    logger.info(f"Processing resource: {resource}")
                    resource_type = resource.get("type", "")
                    resource_name = resource.get("name", "")

                    if resource_type and resource_name:
                        resource_objects.append({
                            "type": resource_type,
                            "name": resource_name
                        })

                logger.info(f"Final resource objects: {resource_objects}")
                return resource_objects
            else:
                logger.warning(f"Failed to fetch resources from {resources_url}. Status: {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"Error fetching resource details from {resources_url}: {e}")
            return []

    def extract_data(self, okta_data):
        logger.info("Extracting data from Okta response")
        formatted_data = []
        for record in okta_data.get("resource-sets", []):
            label = record.get("label", "")
            description = record.get("description", "")
            resources_url = record.get("_links", {}).get("resources", {}).get("href", "")

            # Fetch and format the resource details
            resource_objects = self.get_resource_details(resources_url)

            formatted_data.append(
                {
                    "label": label,
                    "description": description,
                    "resources": resource_objects
                }
            )
        logger.info("Extracted and formatted %d admin resource set records from Okta", len(formatted_data))
        return formatted_data