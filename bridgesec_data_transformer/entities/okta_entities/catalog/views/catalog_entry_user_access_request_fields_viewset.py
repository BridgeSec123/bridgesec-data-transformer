import logging

import requests as http_requests
from django.conf import settings

from core.utils.okta_helpers import get_okta_headers
from entities.views.base_view import BaseEntityViewSet
from entities.okta_entities.catalog.catalog_models import CatalogEntryUserAccessRequestFields
from entities.okta_entities.catalog.catalog_serializers import CatalogEntryUserAccessRequestFieldsSerializer

logger = logging.getLogger(__name__)


class CatalogEntryUserAccessRequestFieldsViewSet(BaseEntityViewSet):
    okta_endpoint = "/governance/api/v2/catalogs/default/entries/{entry_id}/requester-fields"
    entries_endpoint = "/governance/api/v2/catalogs/default/entries"
    entity_type = "catalog_entry_user_access_request_fields"
    serializer_class = CatalogEntryUserAccessRequestFieldsSerializer
    model = CatalogEntryUserAccessRequestFields

    def fetch_and_store_data(self, db_name, request=None):
        try:
            headers = get_okta_headers(request)
            entries_url = f"{self.okta_base_url}{self.entries_endpoint}"

            res = http_requests.get(entries_url, headers=headers)
            if res.status_code != 200:
                logger.error("Failed to fetch catalog entries: %s", res.text)
                return {"error": "Failed to fetch catalog entries"}

            raw = res.json()
            entries = raw if isinstance(raw, list) else raw.get("value", [])

            all_fields = []
            for entry in entries:
                entry_id = entry.get("id", "")
                if not entry_id:
                    continue

                fields_url = (
                    f"{self.okta_base_url}/governance/api/v2/catalogs/default/entries/"
                    f"{entry_id}/requester-fields"
                )
                fields_res = http_requests.get(fields_url, headers=headers)
                if fields_res.status_code != 200:
                    logger.warning("Failed to fetch requester fields for entry %s: %s", entry_id, fields_res.text)
                    continue

                fields = self.extract_data(fields_res.json(), entry_id=entry_id)
                all_fields.extend(fields)

            self.store_data(all_fields, db_name=db_name)
            logger.info("Stored %d Catalog Entry User Access Request Fields records in %s", len(all_fields), db_name)
            return {"okta_catalog_entry_user_access_request_fields": all_fields}

        except Exception as e:
            logger.error("Error in CatalogEntryUserAccessRequestFieldsViewSet.fetch_and_store_data: %s", str(e), exc_info=True)
            return {"error": str(e)}

    def extract_data(self, okta_data, entry_id=""):
        """Extract and format catalog entry user access request fields data"""
        if isinstance(okta_data, dict):
            items = okta_data.get("value", okta_data.get("fields", []))
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
                "entry_id": entry_id,
                "field_id": item.get("id", ""),
                "required": str(item.get("required", "")),
                "type": item.get("type", ""),
                "label": item.get("label", ""),
                "maximum_value": str(item.get("maximumValue", "")),
                "read_only": str(item.get("readOnly", "")),
                "value": str(item.get("value", "")),
                "choices": [c.get("choice", c) if isinstance(c, dict) else str(c)
                            for c in item.get("choices", [])],
            })

        logger.info("Extracted %d Catalog Entry User Access Request Fields records", len(formatted_data))
        return formatted_data
