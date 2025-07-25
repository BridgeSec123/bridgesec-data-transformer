import logging

from core.utils.okta_helpers import get_permissions
from entities.okta_entities.administrators.administrators_models import AdminRoleCustom
from entities.okta_entities.administrators.administrators_serializers import (
    AdminRoleCustomSerializer,
)
from entities.okta_entities.administrators.views.administrators_base_viewset import (
    BaseAdministratorViewSet,
)

logger = logging.getLogger(__name__)

class AdminRoleCustomViewSet(BaseAdministratorViewSet):
    okta_endpoint = "/api/v1/iam/roles"
    entity_type = "okta_admin_role_custom"
    serializer_class = AdminRoleCustomSerializer
    model = AdminRoleCustom

    def extract_data(self, okta_data):
        """
        Format the admin role data from Okta response.
        """
        logger.info("Extracting data from Okta response")
        formatted_data = []
        for record in okta_data.get("roles", []):
            label = record.get("label", "")
            description = record.get("description", "")
            permissions_url = record.get("_links", {}).get("permissions", {}).get("href", "")

            permission = get_permissions(permissions_url) if permissions_url else []

            formatted_data.append(
                {
                    "label": label,
                    "description": description,
                    "permissions": permission
                }
            )
        logger.info("Extracted and formatted %d admin role custom records from Okta", len(formatted_data))
        return formatted_data
