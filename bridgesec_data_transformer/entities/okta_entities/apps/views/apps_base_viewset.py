import logging
from entities.views.base_view import BaseEntityViewSet

logger = logging.getLogger(__name__)

class BaseAppViewSet(BaseEntityViewSet):
    okta_endpoint = "/api/v1/apps"
    entity_type = "apps"
    serializer_class = None
    model = None

    def fetch_and_store_data(self, db_name):
        logger.info("Starting fetch and store process for applications and sub-entities.")
        extracted_data = {}

        from entities.registry import APP_ENTITY_VIEWSETS

        for entity_name, viewset_class in APP_ENTITY_VIEWSETS.items():
            logger.info(f"Processing entity: {entity_name}")
            viewset_instance = viewset_class()

            # Special logic for app_oauth_role_assignment
            if entity_name == "app_oauth_role_assignment":
                extracted_data[entity_name] = []
                for app_oauth in extracted_data.get("okta_apps_oauth", []):
                    client_id = app_oauth.get("client_id")

                    if not client_id:
                        logger.warning("Missing client_id in app_oauth entry. Skipping this record.")
                        continue

                    try:
                        data, _, _ = viewset_instance.fetch_from_okta(client_id)
                    except Exception as e:
                        logger.error(f"Error fetching data from Okta for client_id {client_id}: {e}")
                        continue

                    try:
                        extracted = viewset_instance.extract_data(data, client_id)
                    except Exception as e:
                        logger.error(f"Error extracting data for client_id {client_id}: {e}")
                        continue

                    if extracted:
                        extracted_data[entity_name].extend(extracted)
                    else:
                        logger.info(f"No {entity_name} data extracted for client_id {client_id}. Skipping.")

                continue  # Skip default logic for this entity since it's handled above
            elif entity_name == "okta_app_signon_policy_rule":
                extracted_data[entity_name] = []
                for app_policy in extracted_data.get("okta_app_policy_sign_on", []):
                    policy_id = app_policy.get("id")

                    if not policy_id:
                        logger.warning("Missing policy_id in app_policy entry. Skipping this record.")
                        continue

                    try:
                        data, _, _ = viewset_instance.fetch_from_okta(policy_id)
                    except Exception as e:
                        logger.error(f"Error fetching data from Okta for policy_id {policy_id}: {e}")
                        continue

                    try:
                        extracted = viewset_instance.extract_data(data, policy_id)
                    except Exception as e:
                        logger.error(f"Error extracting data for policy_id {policy_id}: {e}")
                        continue

                    if extracted:
                        extracted_data[entity_name].extend(extracted)
                    else:
                        logger.info(f"No {entity_name} data extracted for policy_id {policy_id}. Skipping.")
                continue  # Skip default logic for this entity since it's handled above
            elif entity_name == "okta_app_oauth_role_assignment":
                extracted_data[entity_name] = []
                for app_oauth in extracted_data.get("okta_app_oauth", []):
                    client_id = app_oauth.get("client_id")

                    if not client_id:
                        logger.warning("Missing client_id in app_oauth entry. Skipping this record.")
                        continue

                    try:
                        data, _, _ = viewset_instance.fetch_from_okta(client_id)
                    except Exception as e:
                        logger.error(f"Error fetching data from Okta for client_id {client_id}: {e}")
                        continue

                    try:
                        extracted = viewset_instance.extract_data(data, client_id)
                    except Exception as e:
                        logger.error(f"Error extracting data for client_id {client_id}: {e}")
                        continue

                    if extracted:
                        extracted_data[entity_name].extend(extracted)
                    else:
                        logger.info(f"No {entity_name} data extracted for client_id {client_id}. Skipping.")
                continue  # Skip default logic for this entity since it's handled above
            # Default logic for all other entities
            extracted_data[entity_name] = []
            try:
                okta_response, _, _ = viewset_instance.fetch_from_okta()
                entity_data = viewset_instance.extract_data(okta_response)
                extracted_data[entity_name].extend(entity_data)
            except Exception as e:
                logger.error(f"Error processing {entity_name}: {e}")
                continue

        # Store all extracted data in DB
        for entity_name, data in extracted_data.items():
            viewset_instance = APP_ENTITY_VIEWSETS[entity_name]()
            try:
                viewset_instance.store_data(data, db_name)
                logger.info(f"Stored {len(data)} records for {entity_name}")
            except Exception as e:
                logger.error(f"Failed to store data for {entity_name}: {e}")

        return extracted_data
