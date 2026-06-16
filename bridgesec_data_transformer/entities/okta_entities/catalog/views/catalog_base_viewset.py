import logging

from entities.views.base_view import BaseEntityViewSet

logger = logging.getLogger(__name__)


class BaseCatalogViewSet(BaseEntityViewSet):
    """
    Base class for handling catalog entities.
    """
    def fetch_and_store_data(self, db_name, request=None):
        logger.info("Starting fetch and store process for catalog entities.")
        extracted_data = {}

        # Import catalog registry here to avoid circular imports
        from entities.registry import CATALOG_ENTITY_VIEWSETS

        for entity_name, viewset_class in CATALOG_ENTITY_VIEWSETS.items():
            logger.info(f"Processing entity: {entity_name}")
            viewset_instance = viewset_class()
            viewset_instance.request = request
            extracted_data[entity_name] = []
            # Fetch full Okta response and extract based on type inside extract_data
            okta_response, _, _ = viewset_instance.fetch_from_okta(request=request)
            entity_data = viewset_instance.extract_data(okta_response)
            extracted_data.setdefault(entity_name, []).extend(entity_data)
            logger.info(f"Extracted {len(extracted_data[entity_name])} records for {entity_name}.")

        for entity_name, data in extracted_data.items():
            viewset_instance = CATALOG_ENTITY_VIEWSETS[entity_name]()
            viewset_instance.request = request
            viewset_instance.store_data(data, db_name)

        return extracted_data
