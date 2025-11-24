import logging

from entities.views.base_view import BaseEntityViewSet
from entities.okta_entities.entitlements.entitlement_models import Entitlement
from entities.okta_entities.entitlements.entitlement_serializers import EntitlementSerializer

logger = logging.getLogger(__name__)


class EntitlementViewSet(BaseEntityViewSet):
    okta_endpoint = "/governance/api/v1/entitlements"
    entity_type = "entitlements"
    serializer_class = EntitlementSerializer
    model = Entitlement

    def extract_data(self, okta_data):
        """Extract and format entitlement data from Okta response"""
        formatted_data = []

        # Check if okta_data is a list or single object
        items = okta_data if isinstance(okta_data, list) else [okta_data]

        for item in items:
            formatted_data.append({
                "data_type": item.get("dataType", ""),
                "external_value": item.get("externalValue", ""),
                "multi_value": item.get("multiValue", False),
                "name": item.get("name", ""),
                "parent": item.get("parent", {}),
                "values": item.get("values", []),
                "description": item.get("description", "")
            })

        logger.info("Extracted %d Entitlement records", len(formatted_data))
        return formatted_data
