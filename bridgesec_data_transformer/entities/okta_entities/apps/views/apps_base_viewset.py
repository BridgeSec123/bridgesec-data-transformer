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
]

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

    def fetch_and_store_data(self, db_name, request=None):
        extracted_data = {}

        from entities.registry import APP_ENTITY_VIEWSETS

        # Step 1: Fetch all apps ONCE
        all_apps = []
        try:
            apps_response, status_code, _ = self.fetch_from_okta(request=request)
            if status_code == 200:
                all_apps = apps_response if isinstance(apps_response, list) else []
                extracted_data["all_apps"] = all_apps
        except Exception as e:
            logger.exception(f"Error fetching apps: {str(e)}")

        # Step 2: Process each entity
        for entity_name, viewset_class in APP_ENTITY_VIEWSETS.items():
            try:
                viewset_instance = viewset_class()
                extracted_data[entity_name] = []

                # Entities that process ALL apps data at once (no iteration)
                if entity_name in ["okta_app_access_policy_assignment", "okta_app_shared_credentials"]:
                    extracted = viewset_instance.extract_data(all_apps)
                    if extracted:
                        extracted_data[entity_name] = extracted
                    store_entity_incrementally(entity_name, extracted_data[entity_name], viewset_instance, db_name)
                    continue

                # Entities that need to iterate through ALL apps (one at a time)
                if entity_name in ENTITIES_NEEDING_APP_ITERATION:
                    for app in all_apps:
                        app_id = app.get("id")
                        app_label = app.get("label")
                        if not app_id:
                            continue
                        try:
                            data, _, _ = viewset_instance.fetch_from_okta(app_id, request=request)
                            app_info = {"app_id": app_id, "label": app_label}
                            extracted = viewset_instance.extract_data(data, app_info)
                            if extracted:
                                extracted_data[entity_name].extend(extracted)
                        except Exception as e:
                            logger.exception(f"Error processing {entity_name} for app_id {app_id}: {str(e)}")
                            continue
                    store_entity_incrementally(entity_name, extracted_data[entity_name], viewset_instance, db_name)
                    continue

                # Entities that iterate over parent entities
                if entity_name in PARENT_ENTITY_MAPPINGS:
                    config = PARENT_ENTITY_MAPPINGS[entity_name]
                    parent_entity = config["parent"]
                    id_field = config["id_field"]
                    no_fetch = config.get("no_fetch", False)

                    parent_data = extracted_data.get(parent_entity, [])

                    if no_fetch:
                        for parent_record in parent_data:
                            try:
                                extracted = viewset_instance.extract_data([parent_record], parent_record)
                                if extracted:
                                    extracted_data[entity_name].extend(extracted)
                            except Exception as e:
                                logger.exception(f"Error processing {entity_name}: {str(e)}")
                                continue
                    else:
                        for parent_record in parent_data:
                            record_id = parent_record.get(id_field)
                            if not record_id:
                                continue
                            try:
                                data, _, _ = viewset_instance.fetch_from_okta(record_id, request=request)
                                extracted = viewset_instance.extract_data(data, parent_record)
                                if extracted:
                                    extracted_data[entity_name].extend(extracted)
                            except Exception as e:
                                logger.exception(f"Error processing {entity_name} for {id_field} {record_id}: {str(e)}")
                                continue

                    if len(extracted_data[entity_name]) > 0:
                        store_entity_incrementally(entity_name, extracted_data[entity_name], viewset_instance, db_name)
                    continue

                # Default logic for regular entities
                try:
                    okta_response, status_code, _ = viewset_instance.fetch_from_okta(request=request)
                    if status_code == 200:
                        entity_data = viewset_instance.extract_data(okta_response)
                        extracted_data[entity_name].extend(entity_data)
                        store_entity_incrementally(entity_name, extracted_data[entity_name], viewset_instance, db_name)
                except Exception as e:
                    logger.exception(f"Error processing {entity_name}: {str(e)}")
                    continue

            except Exception as e:
                logger.exception(f"Error processing {entity_name}: {str(e)}")
                extracted_data[entity_name] = []

        return extracted_data
