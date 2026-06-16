import logging

from entities.views.base_view import BaseEntityViewSet

logger = logging.getLogger(__name__)


class BaseRequestConditionViewSet(BaseEntityViewSet):
    """
    Base class for handling request condition entities.
    """

    def fetch_and_store_data(self, db_name, request=None):
        logger.info("Starting fetch and store process for request condition entities.")
        extracted_data = {}

        from entities.registry import REQUEST_ENTITY_VIEWSETS

        for entity_name, viewset_class in REQUEST_ENTITY_VIEWSETS.items():
            logger.info(f"Processing entity: {entity_name}")
            viewset_instance = viewset_class()
            viewset_instance.request = request
            extracted_data[entity_name] = []

            # If the sub-viewset overrides fetch_and_store_data, delegate fully to it
            if type(viewset_instance).fetch_and_store_data is not BaseEntityViewSet.fetch_and_store_data:
                result = viewset_instance.fetch_and_store_data(db_name, request)
                extracted_data[entity_name] = result.get(entity_name, [])
                logger.info(f"Delegated fetch_and_store_data for {entity_name}: {len(extracted_data[entity_name])} records.")
                continue

            # Default: fetch + extract + store
            okta_response, _, _ = viewset_instance.fetch_from_okta(request=request)
            entity_data = viewset_instance.extract_data(okta_response)
            extracted_data.setdefault(entity_name, []).extend(entity_data)
            logger.info(f"Extracted {len(extracted_data[entity_name])} records for {entity_name}.")

        for entity_name, data in extracted_data.items():
            viewset_instance = REQUEST_ENTITY_VIEWSETS[entity_name]()
            viewset_instance.request = request
            # Skip store for entities that already handled it in fetch_and_store_data
            if type(viewset_instance).fetch_and_store_data is not BaseEntityViewSet.fetch_and_store_data:
                continue
            viewset_instance.store_data(data, db_name)

        return extracted_data
