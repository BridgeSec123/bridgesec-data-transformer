import logging

from entities.views.base_view import BaseEntityViewSet
from entities.okta_entities.api_service_integrations.api_service_integration_models import ApiServiceIntegration
from entities.okta_entities.api_service_integrations.api_service_integration_serializers import ApiServiceIntegrationSerializer

logger = logging.getLogger(__name__)


def _extract_scopes(raw_scopes):
    """Normalise scopes to a flat list of strings regardless of API shape."""
    if not raw_scopes:
        return []
    result = []
    for item in raw_scopes:
        if isinstance(item, str):
            result.append(item)
        elif isinstance(item, dict):
            result.append(item.get("scope", ""))
    return [s for s in result if s]


class ApiServiceIntegrationViewSet(BaseEntityViewSet):
    okta_endpoint = "/api/v1/api-integrations"
    entity_type = "okta_api_service_integration"
    serializer_class = ApiServiceIntegrationSerializer
    model = ApiServiceIntegration

    def extract_data(self, okta_data):
        items = okta_data if isinstance(okta_data, list) else [okta_data]
        formatted_data = []
        for item in items:
            if not isinstance(item, dict):
                logger.warning("Skipping invalid record (not a dict): %s", item)
                continue
            formatted_data.append({
                "api_service_integration_id": item.get("id", ""),
                "type": item.get("type", ""),
                "name": item.get("name", ""),
                "config_guide_url": item.get("configGuideUrl", ""),
                "created": item.get("created", ""),
                "created_at": item.get("createdAt", ""),
                "granted_scopes": _extract_scopes(item.get("grantedScopes") or item.get("granted_scopes")),
            })
        logger.info("Extracted %d API Service Integration records", len(formatted_data))
        return formatted_data

    def fetch_and_store_data(self, db_name, request=None):
        try:
            okta_response, status_code, _ = self.fetch_from_okta(request=request)
            if status_code == 200:
                extracted_data = self.extract_data(okta_response)
                self.store_data(extracted_data, db_name=db_name)
                return {"api_service_integrations": extracted_data}
            return {"api_service_integrations": []}
        except Exception as e:
            logger.exception("Error in ApiServiceIntegrationViewSet.fetch_and_store_data: %s", str(e))
            return {"api_service_integrations": []}
