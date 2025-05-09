import logging

from entities.views.base_view import BaseEntityViewSet

logger = logging.getLogger(__name__)

class BaseBrandViewSet(BaseEntityViewSet):
    """
    Base ViewSet to handle fetching and storing both Brand and their sub entities data dynamically.
    """

    def fetch_and_store_data(self, db_name):
        """
        Fetch brands from Okta, store them in a structured dictionary,
        and pass them to the respective viewsets for storing.
        """
        logger.info("Starting fetch and store process for brands.")

        # Dictionary to store all extracted data
        extracted_data = {}

        # Lazy import to avoid circular import issues
        from entities.registry import BRAND_ENTITY_VIEWSETS
        for entity_name, viewset_class in BRAND_ENTITY_VIEWSETS.items():
            viewset_instance = viewset_class()

            if entity_name == "brands":
                data, status_code, rate_limit = viewset_instance.fetch_from_okta()
                extracted_data[entity_name] = viewset_instance.extract_data(data)

            elif entity_name == "okta_email_domain":
                extracted_data[entity_name] = []
                for brand in extracted_data.get("brands", []):
                    brand_id = brand["brand_id"]
                    data, _, _ = viewset_instance.fetch_from_okta()
                    
                    extracted = viewset_instance.extract_data(data, brand_id)
                    if extracted:
                        extracted_data.setdefault(entity_name, []).extend(extracted)
                    else:
                        logger.info(f"No {entity_name} data extracted for brand {brand_id}. Skipping.")
            else:
                for brand in extracted_data.get("brands", []):
                    brand_id = brand.get("brand_id")
                    if not brand_id:
                        logger.warning("Missing brand_id in brands data, skipping.")
                        continue

                    data = viewset_instance.fetch_from_okta(brand_id)
                    extracted = viewset_instance.extract_data(data, brand_id)
                    if extracted:
                        extracted_data.setdefault(entity_name, []).extend(extracted)
                    else:
                        logger.info(f"No {entity_name} data extracted for brand {brand_id}. Skipping.")
            logger.info(f"Extracted {len(extracted_data[entity_name])} records for {entity_name}.")

        for entity_name, data in extracted_data.items():
            viewset_instance = BRAND_ENTITY_VIEWSETS[entity_name]()
            viewset_instance.store_data(data, db_name)

        return extracted_data
    