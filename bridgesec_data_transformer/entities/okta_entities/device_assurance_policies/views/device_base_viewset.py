import logging

from entities.views.base_view import BaseEntityViewSet

logger = logging.getLogger(__name__)

class BaseDeviceAssurancePolicyViewSet(BaseEntityViewSet):
    """
    Base ViewSet to handle fetching and storing Device Assurance Policies.
    """
    okta_endpoint = "/api/v1/device-assurances"
    def fetch_and_store_data(self, db_name):
        """
        Fetch device assurance policies Okta, store them in a structured dictionary,
        and pass them to the respective viewsets for storing.
        """
        logger.info("Starting fetch and store process for device assurance policies")

        # Dictionary to store all extracted data
        extracted_data = {}

        # Lazy import to avoid circular import issues
        from entities.registry import DEVICE_ASSURANCE_POLICY_ENTITY_VIEWSETS
        for entity_name, viewset_class in DEVICE_ASSURANCE_POLICY_ENTITY_VIEWSETS.items():
            logger.info(f"Processing entity: {entity_name}")
            viewset_instance = viewset_class()
            extracted_data[entity_name] = []
            # Fetch full Okta response and extract based on type inside extract_data
            okta_response, _, _ = viewset_instance.fetch_from_okta()
            entity_data = viewset_instance.extract_data(okta_response)
            extracted_data.setdefault(entity_name, []).extend(entity_data)
            logger.info(f"Extracted {len(extracted_data[entity_name])} records for {entity_name}.")

        for entity_name, data in extracted_data.items():
            viewset_instance = DEVICE_ASSURANCE_POLICY_ENTITY_VIEWSETS[entity_name]()
            viewset_instance.store_data(data, db_name)

        return extracted_data