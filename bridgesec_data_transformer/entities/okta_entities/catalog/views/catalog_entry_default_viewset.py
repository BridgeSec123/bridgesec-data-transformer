import logging

from entities.views.base_view import BaseEntityViewSet
from entities.okta_entities.catalog.catalog_models import CatalogEntryDefault
from entities.okta_entities.catalog.catalog_serializers import CatalogEntryDefaultSerializer

logger = logging.getLogger(__name__)


class CatalogEntryDefaultViewSet(BaseEntityViewSet):
    okta_endpoint = "/governance/api/v2/catalogs/default/entries"
    entity_type = "catalog_entry_default"
    serializer_class = CatalogEntryDefaultSerializer
    model = CatalogEntryDefault

    def extract_data(self, okta_data):
        """Extract and format catalog entry default data from Okta response"""
        if isinstance(okta_data, dict):
            items = okta_data.get("value", okta_data.get("entries", []))
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
                "entry_id": item.get("id", ""),
                "name": item.get("name", ""),
                "requestable": str(item.get("requestable", "")),
                "label": item.get("label", ""),
                "description": item.get("description", ""),
                "parent": item.get("parent", ""),
                "counts": item.get("counts", {}),
            })

        logger.info("Extracted %d Catalog Entry Default records", len(formatted_data))
        return formatted_data
