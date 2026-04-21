import logging
import requests
from core.utils.okta_helpers import get_okta_headers
from rest_framework import status
from rest_framework.response import Response
from django.conf import settings
from core.utils.rate_limit import handle_rate_limit, rate_limit_headers
from core.utils.pagination import fetch_all_pages

from entities.views.base_view import BaseEntityViewSet
from entities.okta_entities.rate_limits.rate_limit_models import PrincipalRateLimit
from entities.okta_entities.rate_limits.rate_limit_serializer import PrincipalRateLimitSerializer

logger = logging.getLogger(__name__)


class PrincipalRateLimitViewSet(BaseEntityViewSet):
    okta_endpoint = "/api/v1/principal-rate-limits"
    entity_type = "principal_rate_limits"
    serializer_class = PrincipalRateLimitSerializer
    model = PrincipalRateLimit

    def fetch_from_okta(self, resource_id=None, request=None):
        """
        Override to fetch principal rate limits for both SSWS_TOKEN and OAUTH_CLIENT types
        """
        all_data = []
        principal_types = ["SSWS_TOKEN", "OAUTH_CLIENT"]
        headers = get_okta_headers(request)

        for principal_type in principal_types:
            # Build the query parameter for filtering
            filter_param = f'principalType eq "{principal_type}"'
            endpoint_with_filter = f"{self.okta_endpoint}?filter={filter_param}"
            okta_url = f"{settings.OKTA_API_URL}/{endpoint_with_filter}"

            logger.info(f"Fetching Principal Rate Limits for type: {principal_type} from {endpoint_with_filter}")

            while True:  # Keep retrying if rate limited
                response = requests.get(okta_url, headers=headers)

                if handle_rate_limit(response):  # Handle rate limit
                    logger.warning("Rate limit reached. Retrying...")
                    continue  # Retry after waiting

                if response.status_code != 200:
                    logger.error(f"Failed to fetch data from Okta: {response.text}")
                    return {"error": f"Failed to fetch data from Okta API: {response.text}"}, response.status_code, rate_limit_headers(response)

                response_data = response.json()

                # Combine responses
                if isinstance(response_data, list):
                    all_data.extend(response_data)
                else:
                    all_data.append(response_data)

                logger.info(f"Fetched {len(response_data) if isinstance(response_data, list) else 1} records for {principal_type}")
                break

        logger.info(f"Total Principal Rate Limits fetched: {len(all_data)}")
        # Return combined data as a list
        return all_data, 200, {}

    def extract_data(self, okta_data):
        items = okta_data if isinstance(okta_data, list) else [okta_data]
        formatted_data = []
        for item in items:
            if not isinstance(item, dict):
                logger.warning("Skipping invalid record (not a dict): %s", item)
                continue
            formatted_data.append({
                "rate_limit_id": item.get("id", ""),
                "principal_id": item.get("principalId", ""),
                "principal_type": item.get("principalType", ""),
                "default_percentage": item.get("defaultPercentage"),
                "default_concurrency_percentage": item.get("defaultConcurrencyPercentage"),
                "created_by": item.get("createdBy", ""),
                "created_date": item.get("createdDate", ""),
                "last_update": item.get("lastUpdate", ""),
                "last_updated_by": item.get("lastUpdatedBy", ""),
                "org_id": item.get("orgId", ""),
            })
        logger.info("Extracted %d Principal Rate Limit records", len(formatted_data))
        return formatted_data