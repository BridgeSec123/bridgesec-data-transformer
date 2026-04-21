import logging

from entities.views.base_view import BaseEntityViewSet
from entities.okta_entities.push_providers.push_provider_models import PushProvider
from entities.okta_entities.push_providers.push_provider_serializers import PushProviderSerializer

logger = logging.getLogger(__name__)

# Sensitive fields the Okta API may include in configuration responses
_SENSITIVE_KEYS = {"privateKey", "tokenSigningKey", "private_key", "token_signing_key"}


def _sanitize_config(value):
    if isinstance(value, dict):
        return {k: _sanitize_config(v) for k, v in value.items() if k not in _SENSITIVE_KEYS}
    return value


class PushProviderViewSet(BaseEntityViewSet):
    okta_endpoint = "/api/v1/push-providers"
    entity_type = "okta_push_provider"
    serializer_class = PushProviderSerializer
    model = PushProvider

    def extract_data(self, okta_data):
        items = okta_data if isinstance(okta_data, list) else [okta_data]
        formatted_data = []
        for item in items:
            if not isinstance(item, dict):
                logger.warning("Skipping invalid record (not a dict): %s", item)
                continue
            formatted_data.append({
                "push_provider_id": item.get("id", ""),
                "name": item.get("name", ""),
                "provider_type": item.get("providerType", ""),
                "last_updated_date": item.get("lastUpdatedDate", ""),
                "configuration": _sanitize_config(item.get("configuration", {})),
            })
        logger.info("Extracted %d Push Provider records", len(formatted_data))
        return formatted_data

    def fetch_and_store_data(self, db_name, request=None):
        try:
            okta_response, status_code, _ = self.fetch_from_okta(request=request)
            if status_code == 200:
                extracted_data = self.extract_data(okta_response)
                self.store_data(extracted_data, db_name=db_name)
                return {"push_providers": extracted_data}
            return {"push_providers": []}
        except Exception as e:
            logger.exception("Error in PushProviderViewSet.fetch_and_store_data: %s", str(e))
            return {"push_providers": []}
