import logging

from entities.views.base_view import BaseEntityViewSet

logger = logging.getLogger(__name__)

class BaseUserViewSet(BaseEntityViewSet):
    """
    Base ViewSet to handle fetching and storing both users and Sub-Entities data dynamically.
    """

    def fetch_and_store_data(self, db_name):
        logger.info("Starting fetch and store process for users and sub-entities.")
        extracted_data = {}

        from entities.registry import USER_ENTITY_VIEWSETS
        for entity_name, viewset_class in USER_ENTITY_VIEWSETS.items():
            viewset_instance = viewset_class()

            if entity_name == 'users':
                data, status_code, rate_limit = viewset_instance.fetch_from_okta()
                users_data = viewset_instance.extract_data(data)
                extracted_data[entity_name] = users_data

                user_ids = [user.get("user_id") for user in users_data]
                logger.info(f"Fetched {len(user_ids)} user IDs for user_factors.")

            elif entity_name == 'user_factors':
                factors_data = []

                for user_id in user_ids:
                    data = viewset_instance.fetch_from_okta(user_id=user_id)
                    extracted = viewset_instance.extract_data(data)
                    factors_data.extend(extracted)

                extracted_data[entity_name] = factors_data
            
            elif entity_name == 'user_admin_roles':
                admin_roles_data = []
                
                for user_id in user_ids:
                    data = viewset_instance.fetch_from_okta(user_id=user_id)
                    extracted = viewset_instance.extract_data(data, user_id)
                    if extracted:
                        admin_roles_data.extend(extracted)
                user_admin_roles_data = admin_roles_data
                extracted_data[entity_name] = admin_roles_data

            elif entity_name == 'okta_admin_role_targets':
                role_targets_data = []

                if not user_admin_roles_data:
                    logger.warning("Skipping okta_admin_role_target due to missing admin roles.")
                    continue

                for item in user_admin_roles_data:
                    user_id = item.get("user_id")
                    role_types = item.get("admin_roles", [])
                    role_ids = item.get("role_ids", [])

                    for role_type, role_id in zip(role_types, role_ids):
                        data = viewset_instance.fetch_from_okta(user_id=user_id, role_id=role_id)
                        extracted = viewset_instance.extract_data(data, user_id=user_id, role_type=role_type)
                        if extracted:
                            role_targets_data.extend(extracted)

                extracted_data[entity_name] = role_targets_data

            elif entity_name == 'okta_role_subscription':
                role_targets_data = []

                # if not user_admin_roles_data:
                #     logger.warning("Skipping okta_admin_role_target due to missing admin roles.")
                #     continue

                for item in extracted_data.get("user_admin_roles", []):
                    role_types = item.get("admin_roles", [])
                    for role_type in role_types:
                        data = viewset_instance.fetch_from_okta(role_type=role_type)
                        extracted = viewset_instance.extract_data(data, role_type=role_type)
                        if extracted:
                            role_targets_data.extend(extracted)

                extracted_data[entity_name] = role_targets_data

            else:
                data, status_code, rate_limit = viewset_instance.fetch_from_okta()
                extracted_data[entity_name] = viewset_instance.extract_data(data)

            logger.info(f"Extracted {len(extracted_data[entity_name])} records for {entity_name}.")

        for entity_name, data in extracted_data.items():
            viewset_instance = USER_ENTITY_VIEWSETS[entity_name]()
            if entity_name == "user_admin_roles":
                # Remove 'role_ids' from each record
                for record in data:
                    record.pop("role_ids", None)
            viewset_instance.store_data(data, db_name)

        return extracted_data
