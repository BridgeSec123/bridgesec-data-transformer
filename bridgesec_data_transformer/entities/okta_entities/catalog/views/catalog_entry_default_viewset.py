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
        formatted_data = []

        # Check if okta_data is a list or single object
        items = okta_data if isinstance(okta_data, list) else [okta_data]

        for item in items:
            formatted_data.append({
                "entry_id": item.get("entryId", "")
            })

        logger.info("Extracted %d Catalog Entry Default records", len(formatted_data))
        return formatted_data
