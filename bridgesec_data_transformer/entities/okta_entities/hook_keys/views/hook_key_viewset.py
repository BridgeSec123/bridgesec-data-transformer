import logging

from entities.views.base_view import BaseEntityViewSet
from entities.okta_entities.hook_keys.hook_key_models import HookKey
from entities.okta_entities.hook_keys.hook_key_serializers import HookKeySerializer

logger = logging.getLogger(__name__)


class HookKeyViewSet(BaseEntityViewSet):
    okta_endpoint = "/api/v1/hook-keys"
    entity_type = "hook_keys"
    serializer_class = HookKeySerializer
    model = HookKey

    def extract_data(self, okta_data):
        items = okta_data if isinstance(okta_data, list) else [okta_data]
        formatted_data = []
        for item in items:
            if not isinstance(item, dict):
                logger.warning("Skipping invalid record (not a dict): %s", item)
                continue
            formatted_data.append({
                "hook_key_id": item.get("id", ""),
                "name": item.get("name", ""),
                "key_id": item.get("keyId", ""),
                "created": item.get("created", ""),
                "is_used": item.get("isUsed", False),
                "last_updated": item.get("lastUpdated", ""),
            })
        logger.info("Extracted %d Hook Key records", len(formatted_data))
        return formatted_data

    def fetch_and_store_data(self, db_name, request=None):
        try:
            okta_response, status_code, _ = self.fetch_from_okta(request=request)
            if status_code == 200:
                extracted_data = self.extract_data(okta_response)
                self.store_data(extracted_data, db_name=db_name)
                return {"hook_keys": extracted_data}
            return {"hook_keys": []}
        except Exception as e:
            logger.exception("Error in HookKeyViewSet.fetch_and_store_data: %s", str(e))
            return {"hook_keys": []}
