import logging

from entities.views.base_view import BaseEntityViewSet

logger = logging.getLogger(__name__)

class BaseAdministratorViewSet(BaseEntityViewSet):
    """
    Base ViewSet to handle fetching and storing both administrators and their sub entities data dynamically.
    """

    def fetch_and_store_data(self, db_name):
        """
        Fetch administrators from Okta, store them in a structured dictionary,
        and pass them to the respective viewsets for storing.
        """
        logger.info("Starting fetch and store process for administrators.")

        # Dictionary to store all extracted data
        extracted_data = {}

        # Lazy import to avoid circular import issues
        from entities.registry import ADMINISTARTORS_ENTITY_VIEWSETS
        for entity_name, viewset_class in ADMINISTARTORS_ENTITY_VIEWSETS.items():
            logger.info(f"Processing entity: {entity_name}")
            viewset_instance = viewset_class()
            extracted_data[entity_name] = []
            # Fetch full Okta response and extract based on type inside extract_data
            okta_response, _, _ = viewset_instance.fetch_from_okta()
            entity_data = viewset_instance.extract_data(okta_response)
            extracted_data.setdefault(entity_name, []).extend(entity_data) # Append to a flat list (not nested by type)

        for entity_name, data in extracted_data.items():
                viewset_instance = ADMINISTARTORS_ENTITY_VIEWSETS[entity_name]()
                viewset_instance.store_data(data, db_name)
                
                logger.info(f"Stored {len(entity_data)} records for {entity_name}")

        return extracted_data
