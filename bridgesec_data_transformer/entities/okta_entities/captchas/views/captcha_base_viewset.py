import logging
from entities.views.base_view import BaseEntityViewSet

logger = logging.getLogger(__name__)

class BaseCaptchaViewSet(BaseEntityViewSet):
    """
    Base class for handling captcha sub-entities.
    """
    def fetch_and_store_data(self, db_name):
        logger.info("Starting fetch and store process for captchas and sub-entities.")
        extracted_data = {}

        # Import your captcha registry here
        from entities.registry import CAPTCHA_ENTITY_VIEWSETS

        for entity_name, viewset_class in CAPTCHA_ENTITY_VIEWSETS.items():
            logger.info(f"Processing entity: {entity_name}")
            viewset_instance = viewset_class()
            extracted_data[entity_name] = []
            # Fetch full Okta response and extract based on type inside extract_data
            okta_response, _, _ = viewset_instance.fetch_from_okta()
            entity_data = viewset_instance.extract_data(okta_response)
            extracted_data.setdefault(entity_name, []).extend(entity_data) # Append to a flat list (not nested by type)

        for entity_name, data in extracted_data.items():
            viewset_instance = CAPTCHA_ENTITY_VIEWSETS[entity_name]()
            viewset_instance.store_data(data, db_name)
            
            logger.info(f"Stored {len(entity_data)} records for {entity_name}")

        return extracted_data
