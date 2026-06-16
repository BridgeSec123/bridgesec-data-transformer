import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

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
                viewset_instance.request = request

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

                    def _fetch_factors(uid, _vi=viewset_instance, _req=request):
                        data = _vi.fetch_from_okta(user_id=uid, request=_req)
                        return _vi.extract_data(data) or []

                    with ThreadPoolExecutor(max_workers=10) as executor:
                        futures = {executor.submit(_fetch_factors, uid): uid for uid in user_ids}
                        for future in as_completed(futures):
                            try:
                                extracted = future.result()
                                if extracted:
                                    factors_data.extend(extracted)
                            except Exception as e:
                                logger.exception(f"Error fetching user_factors: {str(e)}")
                    extracted_data[entity_name] = factors_data

                elif entity_name == 'user_admin_roles':
                    admin_roles_data = []

                    def _fetch_admin_roles(uid, _vi=viewset_instance, _req=request):
                        data = _vi.fetch_from_okta(user_id=uid, request=_req)
                        return _vi.extract_data(data, uid) or []

                    with ThreadPoolExecutor(max_workers=10) as executor:
                        futures = {executor.submit(_fetch_admin_roles, uid): uid for uid in user_ids}
                        for future in as_completed(futures):
                            try:
                                extracted = future.result()
                                if extracted:
                                    admin_roles_data.extend(extracted)
                            except Exception as e:
                                logger.exception(f"Error fetching user_admin_roles: {str(e)}")
                    user_admin_roles_data = admin_roles_data
                    extracted_data[entity_name] = admin_roles_data

                elif entity_name == 'okta_admin_role_targets':
                    role_targets_data = []
                    if not user_admin_roles_data:
                        extracted_data[entity_name] = []
                        continue

                    role_combos = []
                    for item in user_admin_roles_data:
                        uid = item.get("user_id")
                        uname = item.get("user_name")
                        for role_type, role_id in zip(item.get("admin_roles", []), item.get("role_ids", [])):
                            role_combos.append((uid, uname, role_type, role_id))

                    def _fetch_role_targets(combo, _vi=viewset_instance, _req=request):
                        uid, uname, role_type, role_id = combo
                        data = _vi.fetch_from_okta(user_id=uid, role_id=role_id, request=_req)
                        return _vi.extract_data(data, uname, role_type) or []

                    with ThreadPoolExecutor(max_workers=10) as executor:
                        futures = {executor.submit(_fetch_role_targets, combo): combo for combo in role_combos}
                        for future in as_completed(futures):
                            try:
                                extracted = future.result()
                                if extracted:
                                    role_targets_data.extend(extracted)
                            except Exception as e:
                                logger.exception(f"Error fetching okta_admin_role_targets: {str(e)}")
                    extracted_data[entity_name] = role_targets_data

                elif entity_name == 'okta_role_subscription':
                    role_subscriptions_data = []
                    valid_role_types = [
                        'API_ADMIN', 'APP_ADMIN', 'CUSTOM', 'GROUP_MEMBERSHIP_ADMIN',
                        'HELP_DESK_ADMIN', 'MOBILE_ADMIN', 'ORG_ADMIN', 'READ_ONLY_ADMIN',
                        'REPORT_ADMIN', 'SUPER_ADMIN', 'USER_ADMIN'
                    ]

                    def _fetch_role_subscription(role_type, _vi=viewset_instance, _req=request):
                        data = _vi.fetch_from_okta(role_type=role_type, request=_req)
                        return _vi.extract_data(data, role_type=role_type) or []

                    with ThreadPoolExecutor(max_workers=10) as executor:
                        futures = {executor.submit(_fetch_role_subscription, rt): rt for rt in valid_role_types}
                        for future in as_completed(futures):
                            try:
                                extracted = future.result()
                                if extracted:
                                    role_subscriptions_data.extend(extracted)
                            except Exception as e:
                                logger.exception(f"Error fetching okta_role_subscription: {str(e)}")
                    extracted_data[entity_name] = role_subscriptions_data

                elif entity_name == 'okta_user_group_memberships':
                    users_data = extracted_data.get("users", [])
                    group_membership_data = []

                    def _fetch_group_membership(item, _vi=viewset_instance, _req=request):
                        user_id = item.get("user_id")
                        user_name = item.get("first_name")
                        if not user_id:
                            return []
                        data = _vi.fetch_from_okta(user_id=user_id, request=_req)
                        return _vi.extract_data(data, user_name, request=_req) or []

                    with ThreadPoolExecutor(max_workers=10) as executor:
                        futures = {executor.submit(_fetch_group_membership, item): item for item in users_data}
                        for future in as_completed(futures):
                            try:
                                extracted = future.result()
                                if extracted:
                                    group_membership_data.extend(extracted)
                            except Exception as e:
                                logger.exception(f"Error fetching okta_user_group_memberships: {str(e)}")
                    extracted_data[entity_name] = group_membership_data

                elif entity_name == 'okta_user_risk':
                    risk_data = []

                    def _fetch_user_risk(uid, _vi=viewset_instance, _req=request):
                        data = _vi.fetch_from_okta(user_id=uid, request=_req)
                        return _vi.extract_data(data, uid) or []

                    with ThreadPoolExecutor(max_workers=10) as executor:
                        futures = {executor.submit(_fetch_user_risk, uid): uid for uid in user_ids}
                        for future in as_completed(futures):
                            try:
                                extracted = future.result()
                                if extracted:
                                    risk_data.extend(extracted)
                            except Exception as e:
                                logger.exception(f"Error fetching okta_user_risk: {str(e)}")
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
            viewset_instance.request = request
            viewset_instance.store_data(data, db_name)

        return extracted_data_cleaned
