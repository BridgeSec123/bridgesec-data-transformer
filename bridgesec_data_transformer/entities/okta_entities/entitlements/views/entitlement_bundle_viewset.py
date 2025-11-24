import logging

from entities.views.base_view import BaseEntityViewSet
from entities.okta_entities.entitlements.entitlement_models import EntitlementBundle
from entities.okta_entities.entitlements.entitlement_serializers import EntitlementBundleSerializer

logger = logging.getLogger(__name__)


class EntitlementBundleViewSet(BaseEntityViewSet):
    okta_endpoint = "/governance/api/v1/entitlements"
    entity_type = "entitlement_bundles"
    serializer_class = EntitlementBundleSerializer
    model = EntitlementBundle

    def extract_data(self, okta_data):
        """Extract and format entitlement bundle data from Okta response"""
        formatted_data = []

        # Check if okta_data is a list or single object
        items = okta_data if isinstance(okta_data, list) else [okta_data]

        for item in items:
            formatted_data.append({
                "name": item.get("name", ""),
                "target": item.get("target", {}),
                "entitlements": item.get("entitlements", []),
                "description": item.get("description", ""),
                "target_resource_orn": item.get("targetResourceOrn", ""),
                "status": item.get("status", "")
            })

        logger.info("Extracted %d Entitlement Bundle records", len(formatted_data))
        return formatted_data
