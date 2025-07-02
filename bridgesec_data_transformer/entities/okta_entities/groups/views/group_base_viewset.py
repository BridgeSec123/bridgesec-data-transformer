import logging

from entities.views.base_view import BaseEntityViewSet

logger = logging.getLogger(__name__)

class BaseGroupViewSet(BaseEntityViewSet):
    """
    Base ViewSet to handle fetching and storing both Group and Group Membership data dynamically.
    """

    def fetch_and_store_data(self, db_name):
        """
        Fetch groups and their memberships from Okta, store them in a structured dictionary,
        and pass them to the respective viewsets for storing.
        """
        logger.info("Starting fetch and store process for groups and memberships.")

        # Dictionary to store all extracted data
        extracted_data = {}

        # Lazy import to avoid circular import issues
        from entities.registry import GROUP_ENTITY_VIEWSETS
        for entity_name, viewset_class in GROUP_ENTITY_VIEWSETS.items():
            viewset_instance = viewset_class()

            if entity_name == "group" or entity_name == "group_schemas" or entity_name == "group_rules":
                data, status_code, rate_limit = viewset_instance.fetch_from_okta()
                extracted_data[entity_name] = viewset_instance.extract_data(data)
            else:
                extracted_data[entity_name] = []
                for group in extracted_data.get("groups", []):
                    group_id = group["group_id"]
                    data = viewset_instance.fetch_from_okta(group_id)
                    
                    extracted = viewset_instance.extract_data(data, group_id)
                    if extracted:  # Only add if not empty
                        extracted_data.setdefault(entity_name, []).extend(extracted)
                    else:
                        logger.info(f"No {entity_name} data extracted for group {group_id}. Skipping.")

            logger.info(f"Extracted {len(extracted_data[entity_name])} records for {entity_name}.")

        for entity_name, data in extracted_data.items():
            viewset_instance = GROUP_ENTITY_VIEWSETS[entity_name]()
            viewset_instance.store_data(data, db_name)

        return extracted_data