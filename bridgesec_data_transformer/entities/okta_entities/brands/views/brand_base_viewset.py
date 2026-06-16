import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from entities.views.base_view import BaseEntityViewSet

logger = logging.getLogger(__name__)

class BaseBrandViewSet(BaseEntityViewSet):
    """
    Base ViewSet to handle fetching and storing both Brand and their sub entities data dynamically.
    """

    def fetch_and_store_data(self, db_name, request=None):
        extracted_data = {}

        from entities.registry import BRAND_ENTITY_VIEWSETS

        for entity_name, viewset_class in BRAND_ENTITY_VIEWSETS.items():
            try:
                viewset_instance = viewset_class()
                viewset_instance.request = request

                if entity_name == "brands":
                    data, status_code, _ = viewset_instance.fetch_from_okta(request=request)
                    if status_code == 200:
                        extracted_data[entity_name] = viewset_instance.extract_data(data)
                    else:
                        extracted_data[entity_name] = []

                elif entity_name == "okta_email_domain":
                    extracted_data[entity_name] = []
                    for brand in extracted_data.get("brands", []):
                        brand_name = brand["name"]
                        data, status_code, _ = viewset_instance.fetch_from_okta(request=request)
                        if status_code == 200:
                            extracted = viewset_instance.extract_data(data, brand_name)
                            if extracted:
                                extracted_data[entity_name].extend(extracted)

                else:
                    extracted_data[entity_name] = []
                    brands = extracted_data.get("brands", [])

                    def _fetch_brand_entity(brand, _vi=viewset_instance, _en=entity_name, _req=request):
                        brand_id = brand.get("brand_id")
                        brand_name = brand.get("name")
                        if not brand_id:
                            return []
                        data = _vi.fetch_from_okta(brand_id, request=_req)
                        return _vi.extract_data(data, brand_name) or []

                    with ThreadPoolExecutor(max_workers=10) as executor:
                        futures = {executor.submit(_fetch_brand_entity, brand): brand for brand in brands}
                        for future in as_completed(futures):
                            try:
                                extracted = future.result()
                                if extracted:
                                    extracted_data[entity_name].extend(extracted)
                            except Exception as e:
                                logger.exception(f"Error collecting result for {entity_name}: {str(e)}")

            except Exception as e:
                logger.exception(f"Error processing {entity_name}: {str(e)}")
                extracted_data[entity_name] = []

        for entity_name, data in extracted_data.items():
            viewset_instance = BRAND_ENTITY_VIEWSETS[entity_name]()
            viewset_instance.request = request
            viewset_instance.store_data(data, db_name)

        return extracted_data
