import logging

from entities.views.base_view import BaseEntityViewSet
from entities.okta_entities.rate_limits.rate_limit_models import RateLimitWarningThreshold
from entities.okta_entities.rate_limits.rate_limit_serializer import RateLimitWarningThresholdSerializer

logger = logging.getLogger(__name__)


class RateLimitWarningThresholdViewSet(BaseEntityViewSet):
    okta_endpoint = "/api/v1/rate-limit-settings/warning-threshold"
    entity_type = "rate_limit_warning_threshold_percentage"
    serializer_class = RateLimitWarningThresholdSerializer
    model = RateLimitWarningThreshold

    def extract_data(self, okta_data):
        """Extract and format rate limit warning threshold percentage data from Okta response"""
        formatted_data = []

        # Check if okta_data is a list or single object
        items = okta_data if isinstance(okta_data, list) else [okta_data]

        for item in items:
            if not isinstance(item, dict):
                logger.warning(f"Skipping invalid record (not a dict): {item}")
                continue
            formatted_data.append({
                "warning_threshold": item.get("warningThreshold", 90)
            })

        logger.info("Extracted %d Rate Limit Warning Threshold Percentage records", len(formatted_data))
        return formatted_data
