import logging

from entities.views.base_view import BaseEntityViewSet
from entities.okta_entities.api_tokens.api_token_models import ApiToken
from entities.okta_entities.api_tokens.api_token_serializers import ApiTokenSerializer

logger = logging.getLogger(__name__)


class ApiTokenViewSet(BaseEntityViewSet):
    okta_endpoint = "/api/v1/api-tokens"
    entity_type = "api_tokens"
    serializer_class = ApiTokenSerializer
    model = ApiToken

    def extract_data(self, okta_data):
        items = okta_data if isinstance(okta_data, list) else [okta_data]
        formatted_data = []
        for item in items:
            if not isinstance(item, dict):
                logger.warning("Skipping invalid record (not a dict): %s", item)
                continue

            raw_network = item.get("network", {})
            network = {
                "connection": raw_network.get("connection", ""),
                "exclude": raw_network.get("exclude", []),
                "include": raw_network.get("include", []),
            } if isinstance(raw_network, dict) else {}

            formatted_data.append({
                "token_id": item.get("id", ""),
                "name": item.get("name", ""),
                "client_name": item.get("clientName", ""),
                "created": item.get("created", ""),
                "user_id": item.get("userId", ""),
                "network": network,
            })
        logger.info("Extracted %d API Token records", len(formatted_data))
        return formatted_data

    def fetch_and_store_data(self, db_name, request=None):
        try:
            okta_response, status_code, _ = self.fetch_from_okta(request=request)
            if status_code == 200:
                extracted_data = self.extract_data(okta_response)
                self.store_data(extracted_data, db_name=db_name)
                return {"api_tokens": extracted_data}
            return {"api_tokens": []}
        except Exception as e:
            logger.exception("Error in ApiTokenViewSet.fetch_and_store_data: %s", str(e))
            return {"api_tokens": []}
