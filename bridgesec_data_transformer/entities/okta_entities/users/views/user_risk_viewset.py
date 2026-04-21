import logging

import requests
from core.utils.okta_helpers import get_okta_headers
from core.utils.rate_limit import handle_rate_limit
from django.conf import settings

from entities.okta_entities.users.user_models import UserRisk
from entities.okta_entities.users.user_serializers import UserRiskSerializer
from entities.okta_entities.users.views.user_base_viewset import BaseUserViewSet

logger = logging.getLogger(__name__)


class UserRiskViewSet(BaseUserViewSet):
    okta_endpoint = "api/v1/users/{user_id}/risk"
    entity_type = "okta_user_risk"
    serializer_class = UserRiskSerializer
    model = UserRisk

    def fetch_from_okta(self, user_id, request=None):
        if not user_id:
            logger.error("user_id is required to fetch user risk.")
            return {}

        okta_url = f"{settings.OKTA_API_URL}/{self.okta_endpoint.format(user_id=user_id)}"
        headers = get_okta_headers(request)

        while True:
            response = requests.get(okta_url, headers=headers)

            if handle_rate_limit(response):
                logger.warning("Rate limit reached fetching user risk. Retrying...")
                continue

            if response.status_code == 404:
                logger.debug("No risk record for user %s", user_id)
                return {}

            if response.status_code != 200:
                logger.error("Failed to fetch user risk for %s: %s", user_id, response.text)
                return {}

            return response.json()

    def extract_data(self, okta_data, user_id):
        if not okta_data or not isinstance(okta_data, dict):
            return []

        reasons = okta_data.get("reasons") or []
        reason_str = ", ".join(reasons) if isinstance(reasons, list) else str(reasons)

        return [{
            "user_id": user_id,
            "risk_id": okta_data.get("id", ""),
            "risk_level": okta_data.get("riskLevel", "NONE"),
            "reason": reason_str,
        }]
