import logging

from core.utils.entity_mapping import clean_entity_data
from entities.views.base_view import BaseEntityViewSet

logger = logging.getLogger(__name__)

class BaseUserViewSet(BaseEntityViewSet):
    """
    Base ViewSet to handle fetching and storing both users and Sub-Entities data dynamically.
    """

    def fetch_and_store_data(self, db_name, request=None):
        extracted_data = {}
        user_ids = []
        user_admin_roles_data = []

        from entities.registry import USER_ENTITY_VIEWSETS

        for entity_name, viewset_class in USER_ENTITY_VIEWSETS.items():
            try:
                viewset_instance = viewset_class()

                if entity_name == 'users':
                    data, status_code, rate_limit = viewset_instance.fetch_from_okta(request=request)
                    if status_code == 200:
                        users_data = viewset_instance.extract_data(data)
                        extracted_data[entity_name] = users_data
                        user_ids = [user.get("user_id") for user in users_data if user.get("user_id")]
                    else:
                        extracted_data[entity_name] = []

                elif entity_name == 'user_factors':
                    factors_data = []
                    for user_id in user_ids:
                        data = viewset_instance.fetch_from_okta(user_id=user_id, request=request)
                        extracted = viewset_instance.extract_data(data)
                        factors_data.extend(extracted)
                    extracted_data[entity_name] = factors_data

                elif entity_name == 'user_admin_roles':
                    admin_roles_data = []
                    for user_id in user_ids:
                        data = viewset_instance.fetch_from_okta(user_id=user_id, request=request)
                        extracted = viewset_instance.extract_data(data, user_id)
                        if extracted:
                            admin_roles_data.extend(extracted)
                    user_admin_roles_data = admin_roles_data
                    extracted_data[entity_name] = admin_roles_data

                elif entity_name == 'okta_admin_role_targets':
                    role_targets_data = []
                    if not user_admin_roles_data:
                        extracted_data[entity_name] = []
                        continue

                    for item in user_admin_roles_data:
                        user_id = item.get("user_id")
                        user_name = item.get("user_name")
                        role_types = item.get("admin_roles", [])
                        role_ids = item.get("role_ids", [])

                        for role_type, role_id in zip(role_types, role_ids):
                            data = viewset_instance.fetch_from_okta(user_id=user_id, role_id=role_id, request=request)
                            extracted = viewset_instance.extract_data(data, user_name, role_type)
                            if extracted:
                                role_targets_data.extend(extracted)

                    extracted_data[entity_name] = role_targets_data

                elif entity_name == 'okta_role_subscription':
                    role_subscriptions_data = []
                    valid_role_types = [
                        'API_ADMIN', 'APP_ADMIN', 'CUSTOM', 'GROUP_MEMBERSHIP_ADMIN',
                        'HELP_DESK_ADMIN', 'MOBILE_ADMIN', 'ORG_ADMIN', 'READ_ONLY_ADMIN',
                        'REPORT_ADMIN', 'SUPER_ADMIN', 'USER_ADMIN'
                    ]
                    for role_type in valid_role_types:
                        data = viewset_instance.fetch_from_okta(role_type=role_type, request=request)
                        extracted = viewset_instance.extract_data(data, role_type=role_type)
                        if extracted:
                            role_subscriptions_data.extend(extracted)
                    extracted_data[entity_name] = role_subscriptions_data

                elif entity_name == 'okta_user_group_memberships':
                    users_data = extracted_data.get("users", [])
                    group_membership_data = []

                    for item in users_data:
                        user_id = item.get("user_id")
                        user_name = item.get("first_name")
                        if not user_id:
                            continue

                        data = viewset_instance.fetch_from_okta(user_id=user_id, request=request)
                        extracted = viewset_instance.extract_data(data, user_name, request=request)

                        if extracted:
                            group_membership_data.extend(extracted)

                    extracted_data[entity_name] = group_membership_data

                elif entity_name == 'okta_user_risk':
                    risk_data = []
                    for user_id in user_ids:
                        data = viewset_instance.fetch_from_okta(user_id=user_id, request=request)
                        extracted = viewset_instance.extract_data(data, user_id)
                        if extracted:
                            risk_data.extend(extracted)
                    extracted_data[entity_name] = risk_data

                else:
                    data, status_code, rate_limit = viewset_instance.fetch_from_okta(request=request)
                    if status_code == 200:
                        extracted_data[entity_name] = viewset_instance.extract_data(data)
                    else:
                        extracted_data[entity_name] = []

            except Exception as e:
                logger.exception(f"Error processing {entity_name}: {str(e)}")
                extracted_data[entity_name] = []

        extracted_data_cleaned = {
            entity: clean_entity_data(entity, data)
            for entity, data in extracted_data.items()
        }

        for entity_name, data in extracted_data_cleaned.items():
            viewset_instance = USER_ENTITY_VIEWSETS[entity_name]()
            viewset_instance.store_data(data, db_name)

        return extracted_data_cleaned
