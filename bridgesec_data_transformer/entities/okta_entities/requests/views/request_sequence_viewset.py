import logging

import requests as http_requests
from django.conf import settings

from core.utils.okta_helpers import get_okta_headers
from entities.views.base_view import BaseEntityViewSet
from entities.okta_entities.requests.request_condition_models import RequestSequence
from entities.okta_entities.requests.request_condition_serializers import RequestSequenceSerializer

logger = logging.getLogger(__name__)


class RequestSequenceViewSet(BaseEntityViewSet):
    okta_endpoint = "/governance/api/v2/resources/{resource_id}/access-request-settings/approval-sequences"
    resources_endpoint = "/governance/api/v2/resources"
    entity_type = "request_sequences"
    serializer_class = RequestSequenceSerializer
    model = RequestSequence

    def fetch_and_store_data(self, db_name, request=None):
        try:
            headers = get_okta_headers(request)
            resources_url = f"{self.okta_base_url}{self.resources_endpoint}"

            res = http_requests.get(resources_url, headers=headers)
            if res.status_code != 200:
                logger.error("Failed to fetch resources: %s", res.text)
                return {"error": "Failed to fetch resources"}

            raw = res.json()
            resources = raw if isinstance(raw, list) else raw.get("value", [])

            all_sequences = []
            for resource in resources:
                resource_id = resource.get("id", "")
                if not resource_id:
                    continue

                sequences_url = (
                    f"{self.okta_base_url}/governance/api/v2/resources/"
                    f"{resource_id}/access-request-settings/approval-sequences"
                )
                seq_res = http_requests.get(sequences_url, headers=headers)
                if seq_res.status_code != 200:
                    logger.warning("Failed to fetch sequences for resource %s: %s", resource_id, seq_res.text)
                    continue

                sequences = self.extract_data(seq_res.json(), resource_id=resource_id)
                all_sequences.extend(sequences)

            self.store_data(all_sequences, db_name=db_name)
            logger.info("Stored %d Request Sequence records in %s", len(all_sequences), db_name)
            return {"okta_request_sequences": all_sequences}

        except Exception as e:
            logger.error("Error in RequestSequenceViewSet.fetch_and_store_data: %s", str(e), exc_info=True)
            return {"error": str(e)}

    def extract_data(self, okta_data, resource_id=""):
        """Extract and format request sequence data from Okta response"""
        if isinstance(okta_data, dict):
            items = okta_data.get("value", okta_data.get("sequences", []))
        elif isinstance(okta_data, list):
            items = okta_data
        else:
            items = []

        formatted_data = []
        for item in items:
            if not isinstance(item, dict):
                logger.warning("Skipping invalid record (not a dict): %s", item)
                continue
            formatted_data.append({
                "sequence_id": item.get("id", ""),
                "resource_id": resource_id or item.get("resourceId", ""),
            })

        logger.info("Extracted %d Request Sequence records", len(formatted_data))
        return formatted_data
