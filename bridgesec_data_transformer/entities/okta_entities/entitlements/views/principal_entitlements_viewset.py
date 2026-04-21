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

        # API may return a dict with "data" key or a list directly
        if isinstance(okta_data, dict):
            items = okta_data.get("data", [])
        elif isinstance(okta_data, list):
            # Each list item may itself be a wrapper with "data"
            items = []
            for entry in okta_data:
                if isinstance(entry, dict) and "data" in entry:
                    items.extend(entry["data"])
                elif isinstance(entry, dict):
                    items.append(entry)
        else:
            items = []

        for item in items:
            if not isinstance(item, dict):
                logger.warning(f"Skipping invalid record (not a dict): {item}")
                continue
            formatted_data.append({
                "entitlement_id": item.get("id", ""),
                "name": item.get("name", ""),
                "description": item.get("description", ""),
                "data_type": item.get("dataType", ""),
                "multi_value": item.get("multiValue", False),
                "required": item.get("required", False),
                "external_value": item.get("externalValue", ""),
                "parent_resource_orn": item.get("parentResourceOrn", ""),
                "target_principal_orn": item.get("targetPrincipalOrn", ""),
                "parent": item.get("parent", {}),
                "target_principal": item.get("targetPrincipal", {}),
                "values": [
                    {
                        "id": v.get("id", ""),
                        "name": v.get("name", ""),
                        "description": v.get("description", ""),
                        "external_id": v.get("externalId", ""),
                        "external_value": v.get("externalValue", ""),
                    }
                    for v in item.get("values", [])
                    if isinstance(v, dict)
                ],
            })

        logger.info("Extracted %d Principal Entitlement records", len(formatted_data))
        return formatted_data
