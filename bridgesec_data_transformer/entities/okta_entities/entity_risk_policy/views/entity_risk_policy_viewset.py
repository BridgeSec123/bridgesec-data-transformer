import logging

import requests
from core.utils.okta_helpers import get_okta_headers
from core.utils.pagination import fetch_all_pages
from core.utils.rate_limit import handle_rate_limit, rate_limit_headers
from django.conf import settings

from entities.okta_entities.entity_risk_policy.entity_risk_policy_models import EntityRiskPolicy
from entities.okta_entities.entity_risk_policy.entity_risk_policy_serializers import EntityRiskPolicySerializer
from entities.views.base_view import BaseEntityViewSet

logger = logging.getLogger(__name__)


class EntityRiskPolicyViewSet(BaseEntityViewSet):
    okta_endpoint = "api/v1/policies"
    entity_type = "okta_entity_risk_policy"
    serializer_class = EntityRiskPolicySerializer
    model = EntityRiskPolicy

    def fetch_from_okta(self, request=None):
        okta_url = f"{settings.OKTA_API_URL}/{self.okta_endpoint}?type=ENTITY_RISK"
        headers = get_okta_headers(request)

        while True:
            response = requests.get(okta_url, headers=headers)

            if handle_rate_limit(response):
                logger.warning("Rate limit reached fetching entity risk policies. Retrying...")
                continue

            if response.status_code != 200:
                logger.error("Failed to fetch entity risk policies: %s", response.text)
                return [], response.status_code, rate_limit_headers(response)

            response_data = response.json()
            next_url = response.links.get("next", {}).get("url")
            if next_url:
                response_data = fetch_all_pages(okta_url, headers)

            logger.info("Fetched %d entity risk policies", len(response_data))
            return response_data, 200, rate_limit_headers(response)

    def extract_data(self, okta_data):
        items = okta_data if isinstance(okta_data, list) else [okta_data]
        result = []
        for item in items:
            if not isinstance(item, dict):
                continue
            result.append({
                "policy_id": item.get("id", ""),
                "name": item.get("name", ""),
                "status": item.get("status", ""),
            })
        logger.info("Extracted %d entity risk policy records", len(result))
        return result
