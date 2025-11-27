import logging

from entities.views.base_view import BaseEntityViewSet
from entities.okta_entities.entitlements.entitlement_models import PrincipalEntitlement
from entities.okta_entities.entitlements.entitlement_serializers import PrincipalEntitlementSerializer

logger = logging.getLogger(__name__)


class PrincipalEntitlementsViewSet(BaseEntityViewSet):
    okta_endpoint = "/governance/api/v1/principal-entitlements"
    entity_type = "principal_entitlements"
    serializer_class = PrincipalEntitlementSerializer
    model = PrincipalEntitlement

    def extract_data(self, okta_data):
        """Extract and format principal entitlements data from Okta response"""
        formatted_data = []

        # Check if okta_data is a list or single object
        items = okta_data if isinstance(okta_data, list) else [okta_data]

        for item in items:
            if not isinstance(item, dict):
                logger.warning(f"Skipping invalid record (not a dict): {item}")
                continue
            formatted_data.append({
                "parent": item.get("parent", {}),
                "target_principal": item.get("targetPrincipal", {})
            })

        logger.info("Extracted %d Principal Entitlement records", len(formatted_data))
        return formatted_data
