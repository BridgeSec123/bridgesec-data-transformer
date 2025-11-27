import logging

from entities.views.base_view import BaseEntityViewSet

logger = logging.getLogger(__name__)


class BaseLinkViewSet(BaseEntityViewSet):
    """
    Base ViewSet to handle fetching and storing both Link and their sub entities data dynamically.
    """

    def fetch_and_store_data(self, db_name, request=None):
        """
        Fetch Link from Okta, store them in a structured dictionary,
        and pass them to the respective viewsets for storing.
        """
        logger.info("Starting fetch and store process for Link.")

        extracted_data = {}

        from entities.registry import LINK_ENTITY_VIEWSETS

        for entity_name, viewset_class in LINK_ENTITY_VIEWSETS.items():
            logger.info(f"Processing entity: {entity_name}")
            viewset_instance = viewset_class()
            extracted_data[entity_name] = []

            # Fetch full Okta response and extract based on type inside extract_data
            okta_response, _, _ = viewset_instance.fetch_from_okta(request=request)
            entity_data = viewset_instance.extract_data(okta_response)
            extracted_data.setdefault(entity_name, []).extend(entity_data)

        for entity_name, data in extracted_data.items():
            viewset_instance = LINK_ENTITY_VIEWSETS[entity_name]()
            viewset_instance.store_data(data, db_name)
            logger.info(f"Stored {len(data)} records for {entity_name}")

        return extracted_data
