import logging

from core.utils.entity_mapping import clean_entity_data

from entities.views.base_view import BaseEntityViewSet

logger = logging.getLogger(__name__)

class BaseAuthServerViewSet(BaseEntityViewSet):
    """
    Base ViewSet to handle fetching and storing both Auth Servers and Sub-Entities data dynamically.
    """

    def fetch_and_store_data(self, db_name):
        logger.info("Starting fetch and store process for auth server and sub-entities.")
        extracted_data = {}

        from entities.registry import AUTH_SERVER_ENTITY_VIEWSETS
        for entity_name, viewset_class in AUTH_SERVER_ENTITY_VIEWSETS.items():
            viewset_instance = viewset_class()

            if entity_name == "auth_servers" or entity_name == "auth_servers_default":
                data, status_code, rate_limit = viewset_instance.fetch_from_okta()
                extracted_data[entity_name] = viewset_instance.extract_data(data)
            
            elif entity_name == "auth_server_policy_rules":
                extracted_data[entity_name] = []
                for policy in extracted_data.get("auth_server_policy", []):
                    auth_server_id = policy.get("auth_server_id")
                    policy_id = policy.get("policy_id")
                    data = viewset_instance.fetch_from_okta(auth_server_id, policy_id)
                    extracted = viewset_instance.extract_data(data, auth_server_id, policy_id)
                    if extracted:
                        extracted_data[entity_name].extend(extracted)
            
            else:
                extracted_data[entity_name] = []
                # Loop through all auth_servers to get auth_server_id
                for auth_server in extracted_data.get("auth_servers", []):
                    auth_server_id = auth_server.get("auth_server_id")
                    if not auth_server_id:
                        logger.warning("Missing auth_server_id in auth_servers data, skipping.")
                        continue

                    data = viewset_instance.fetch_from_okta(auth_server_id)
                    extracted = viewset_instance.extract_data(data, auth_server_id)

                    if extracted:
                        extracted_data[entity_name].extend(extracted)
                    else:
                        logger.info(f"No {entity_name} data extracted for auth server {auth_server_id}. Skipping.")

            logger.info(f"Extracted {len(extracted_data[entity_name])} records for {entity_name}.")

        extracted_data_cleaned = {
            entity: clean_entity_data(entity, data)
            for entity, data in extracted_data.items()
        }

        logger.info(f"Extracted {len(extracted_data[entity_name])} records for {entity_name}.")

        for entity_name, data in extracted_data_cleaned.items():
            viewset_instance = AUTH_SERVER_ENTITY_VIEWSETS[entity_name]()
            viewset_instance.store_data(data, db_name)

        return extracted_data_cleaned

