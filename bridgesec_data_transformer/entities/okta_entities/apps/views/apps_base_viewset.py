import logging

from core.utils.entity_mapping import clean_entity_data
from core.utils.mongo_utils import store_entity_incrementally
from entities.views.base_view import BaseEntityViewSet

logger = logging.getLogger(__name__)

ENTITIES_NEEDING_APP_ITERATION = [
    "okta_app_group_assignment",
    "okta_app_group_assignments",
    "okta_app_users",
    "okta_app_user_schema_property",
    "okta_app_user_base_schema_property"
    # Add more entities here that need per-app iteration
]

# Define entities that iterate over other parent entities
PARENT_ENTITY_MAPPINGS = {
    "app_oauth_role_assignment": {"parent": "okta_app_oauth", "id_field": "client_id"},
    "okta_app_oauth_role_assignment": {"parent": "okta_app_oauth", "id_field": "client_id"},
    "okta_app_signon_policy_rule": {"parent": "okta_app_policy_sign_on", "id_field": "app_policy_id"},
    "okta_app_oauth_api_scope": {"parent": "okta_app_oauth", "id_field": "app_id"},
    "okta_apps_oauth_redirect_uri": {"parent": "okta_app_oauth", "id_field": "app_id", "no_fetch": True},
    "okta_apps_oauth_post_redirect_uri": {"parent": "okta_app_oauth", "id_field": "app_id", "no_fetch": True},
}

class BaseAppViewSet(BaseEntityViewSet):
    okta_endpoint = "/api/v1/apps?limit=200"
    entity_type = "apps"
    serializer_class = None
    model = None

    def fetch_and_store_data(self, db_name):
        logger.info("Starting fetch and store process for applications and sub-entities.")
        extracted_data = {}

        from entities.registry import APP_ENTITY_VIEWSETS

        # Step 1: Fetch all apps ONCE and store them
        all_apps = [] 
        try:
            logger.info("Fetching all applications from Okta...")
            apps_response, _, _ = self.fetch_from_okta()
            # Store raw apps data (not extracted) for iteration
            all_apps = apps_response if isinstance(apps_response, list) else []
            extracted_data["all_apps"] = all_apps  # Store for later use
            logger.info(f"Fetched {len(all_apps)} applications from Okta")
        except Exception as e:
            logger.error(f"Error fetching apps: {e}")

        # Step 2: Process each entity
        for entity_name, viewset_class in APP_ENTITY_VIEWSETS.items():
            logger.info(f"Processing entity: {entity_name}")
            viewset_instance = viewset_class()
            extracted_data[entity_name] = []

            # Entities that process ALL apps data at once (no iteration)
            if entity_name in ["okta_app_access_policy_assignment", "okta_app_shared_credentials"]:
                logger.info(f"{entity_name} processes ALL apps data at once (no per-app iteration)")
                try:
                    extracted = viewset_instance.extract_data(all_apps)
                    if extracted:
                        extracted_data[entity_name] = extracted
                    logger.info(f"Completed {entity_name}: {len(extracted_data[entity_name])} records")

                    # Store immediately after extraction
                    store_entity_incrementally(entity_name, extracted_data[entity_name], viewset_instance, db_name)
                except Exception as e:
                    logger.error(f"Error processing {entity_name}: {e}")
                continue

            # Check if this entity needs to iterate through ALL apps (one at a time)
            if entity_name in ENTITIES_NEEDING_APP_ITERATION:
                logger.info(f"{entity_name} needs per-app iteration. Iterating through {len(all_apps)} apps...")
                for app in all_apps:
                    app_id = app.get("id")
                    app_label = app.get("label")
                    if not app_id:
                        logger.warning(f"Missing app_id in app entry. Skipping.")
                        continue
                    try:
                        data, _, _ = viewset_instance.fetch_from_okta(app_id)
                        app_info = {"app_id": app_id, "label": app_label}
                        extracted = viewset_instance.extract_data(data, app_info)
                        if extracted:
                            extracted_data[entity_name].extend(extracted)
                    except Exception as e:
                        logger.error(f"Error processing {entity_name} for app_id {app_id}: {e}")
                        continue
                logger.info(f"Completed {entity_name}: {len(extracted_data[entity_name])} records")


                # Store immediately after extraction
                store_entity_incrementally(entity_name, extracted_data[entity_name], viewset_instance, db_name)
                continue

            if entity_name in PARENT_ENTITY_MAPPINGS:
                config = PARENT_ENTITY_MAPPINGS[entity_name]
                parent_entity = config["parent"]
                id_field = config["id_field"]
                no_fetch = config.get("no_fetch", False)

                logger.info(f"{entity_name} needs to iterate through {parent_entity} (no_fetch={no_fetch})")
                parent_data = extracted_data.get(parent_entity, [])
                logger.info(f"Found {len(parent_data)} parent records for {entity_name} from {parent_entity}")

                if no_fetch:
                    # Entities that don't need to fetch from Okta, just extract from parent data
                    logger.info(f"{entity_name} extracts data directly from parent {parent_entity} without Okta API calls")
                    for parent_record in parent_data:
                        try:
                            extracted = viewset_instance.extract_data([parent_record], parent_record)
                            if extracted:
                                extracted_data[entity_name].extend(extracted)
                        except Exception as e:
                            logger.error(f"Error processing {entity_name} for parent record: {e}")
                            continue
                else:
                    # Entities that need to fetch from Okta for each parent record
                    for parent_record in parent_data:
                        record_id = parent_record.get(id_field)
                        if not record_id:
                            logger.warning(f"Missing {id_field} in {parent_entity}. Skipping.")
                            continue

                        try:
                            # Fetch data from Okta and pass parent_record to extract_data
                            data, _, _ = viewset_instance.fetch_from_okta(record_id)
                            extracted = viewset_instance.extract_data(data, parent_record)

                            if extracted:
                                extracted_data[entity_name].extend(extracted)
                        except Exception as e:
                            logger.error(f"Error processing {entity_name} for {id_field} {record_id}: {e}")
                            continue

                logger.info(f"Completed {entity_name}: {len(extracted_data[entity_name])} records")

                # Store immediately after extraction
                if len(extracted_data[entity_name]) > 0:
                    logger.info(f"Storing {len(extracted_data[entity_name])} records for {entity_name}")
                    store_entity_incrementally(entity_name, extracted_data[entity_name], viewset_instance, db_name)
                else:
                    logger.warning(f"No records to store for {entity_name}. Skipping storage.")
                continue

            # Default logic for regular entities
            try:
                okta_response, _, _ = viewset_instance.fetch_from_okta()
                entity_data = viewset_instance.extract_data(okta_response)
                extracted_data[entity_name].extend(entity_data)
                logger.info(f"Completed {entity_name}: {len(entity_data)} records")

                # Store immediately after extraction
                store_entity_incrementally(entity_name, extracted_data[entity_name], viewset_instance, db_name)
            except Exception as e:
                logger.error(f"Error processing {entity_name}: {e}")
                continue

        logger.info("All app entities have been processed and stored incrementally.")
        return extracted_data
