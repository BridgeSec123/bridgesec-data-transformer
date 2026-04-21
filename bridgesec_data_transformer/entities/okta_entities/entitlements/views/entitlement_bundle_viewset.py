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
        items = okta_data if isinstance(okta_data, list) else [okta_data]
        formatted_data = []

        for item in items:
            if not isinstance(item, dict):
                logger.warning("Skipping invalid record (not a dict): %s", item)
                continue

            raw_entitlements = item.get("entitlements", [])
            entitlements = []
            for e in (raw_entitlements if isinstance(raw_entitlements, list) else []):
                if not isinstance(e, dict):
                    continue
                raw_values = e.get("values", [])
                entitlements.append({
                    "id": e.get("id", ""),
                    "name": e.get("name", ""),
                    "description": e.get("description", ""),
                    "data_type": e.get("dataType", ""),
                    "external_value": e.get("externalValue", ""),
                    "multi_value": e.get("multiValue", False),
                    "required": e.get("required", False),
                    "values": [
                        {
                            "id": v.get("id", ""),
                            "name": v.get("name", ""),
                            "description": v.get("description", ""),
                            "external_id": v.get("externalId", ""),
                            "external_value": v.get("externalValue", ""),
                        }
                        for v in (raw_values if isinstance(raw_values, list) else [])
                        if isinstance(v, dict)
                    ],
                })

            raw_target = item.get("target", {})
            target = {
                "external_id": raw_target.get("externalId", ""),
                "type": raw_target.get("type", ""),
            } if isinstance(raw_target, dict) else {}

            formatted_data.append({
                "bundle_id": item.get("id", ""),
                "name": item.get("name", ""),
                "description": item.get("description", ""),
                "target_resource_orn": item.get("targetResourceOrn", ""),
                "status": item.get("status", ""),
                "target": target,
                "entitlements": entitlements,
                "created": item.get("created", ""),
                "last_updated": item.get("lastUpdated", ""),
                "created_by": item.get("createdBy", ""),
                "last_updated_by": item.get("lastUpdatedBy", ""),
            })

        logger.info("Extracted %d Entitlement Bundle records", len(formatted_data))
        return formatted_data
