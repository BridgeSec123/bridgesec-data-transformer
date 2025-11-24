import logging

from entities.views.base_view import BaseEntityViewSet
from entities.okta_entities.catalog.catalog_models import CatalogEntryUserAccessRequestFields
from entities.okta_entities.catalog.catalog_serializers import CatalogEntryUserAccessRequestFieldsSerializer

logger = logging.getLogger(__name__)


class CatalogEntryUserAccessRequestFieldsViewSet(BaseEntityViewSet):
    okta_endpoint = "/governance/api/v2/catalogs/default/user"
    entity_type = "catalog_entry_user_access_request_fields"
    serializer_class = CatalogEntryUserAccessRequestFieldsSerializer
    model = CatalogEntryUserAccessRequestFields

    def extract_data(self, okta_data):
        """Extract and format catalog entry user access request fields data from Okta response"""
        formatted_data = []

        # Check if okta_data is a list or single object
        items = okta_data if isinstance(okta_data, list) else [okta_data]

        for item in items:
            formatted_data.append({
                "entry_id": item.get("entryId", ""),
                "user_id": item.get("userId", "")
            })

        logger.info("Extracted %d Catalog Entry User Access Request Fields records", len(formatted_data))
        return formatted_data
