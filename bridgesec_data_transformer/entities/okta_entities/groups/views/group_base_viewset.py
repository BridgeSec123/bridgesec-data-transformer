import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from core.utils.entity_mapping import clean_entity_data
from entities.views.base_view import BaseEntityViewSet

logger = logging.getLogger(__name__)

class BaseGroupViewSet(BaseEntityViewSet):
    """
    Base ViewSet to handle fetching and storing both Group and Group Membership data dynamically.
    """

    def fetch_and_store_data(self, db_name, request=None):
        logger.info("Starting fetch and store process for groups and memberships.")

        extracted_data = {}

        from entities.registry import GROUP_ENTITY_VIEWSETS
        for entity_name, viewset_class in GROUP_ENTITY_VIEWSETS.items():
            viewset_instance = viewset_class()
            viewset_instance.request = request

            if entity_name == "group" or entity_name == "group_schemas" or entity_name == "group_rules":
                data, status_code, rate_limit = viewset_instance.fetch_from_okta(request=request)
                extracted_data[entity_name] = viewset_instance.extract_data(data)
            else:
                extracted_data[entity_name] = []
                groups = extracted_data.get("group", [])

                def _fetch_group_entity(group, _vi=viewset_instance, _en=entity_name, _req=request):
                    group_id = group["group_id"]
                    data = _vi.fetch_from_okta(group_id, request=_req)
                    return _vi.extract_data(data, group_id) or []

                with ThreadPoolExecutor(max_workers=10) as executor:
                    futures = {executor.submit(_fetch_group_entity, group): group for group in groups}
                    for future in as_completed(futures):
                        try:
                            extracted = future.result()
                            if extracted:
                                extracted_data[entity_name].extend(extracted)
                            else:
                                logger.info(f"No {entity_name} data extracted for a group. Skipping.")
                        except Exception as e:
                            logger.exception(f"Error collecting result for {entity_name}: {str(e)}")

            logger.info(f"Extracted {len(extracted_data[entity_name])} records for {entity_name}.")

        extracted_data_cleaned = {
            entity: clean_entity_data(entity, data)
            for entity, data in extracted_data.items()
        }

        logger.info(f"Extracted {len(extracted_data[entity_name])} records for {entity_name}.")

        for entity_name, data in extracted_data_cleaned.items():
            viewset_instance = GROUP_ENTITY_VIEWSETS[entity_name]()
            viewset_instance.request = request
            viewset_instance.store_data(data, db_name)

        return extracted_data
