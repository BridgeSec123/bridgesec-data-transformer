import logging

from core.utils.entity_mapping import clean_entity_data
from entities.views.base_view import BaseEntityViewSet

logger = logging.getLogger(__name__)


class BasePolicyViewSet(BaseEntityViewSet):
    """
    Base ViewSet to handle fetching and storing both policies and Sub-Entities data dynamically.
    """

    def fetch_and_store_data(self, db_name, request=None):
        logger.info("Starting fetch and store process for policies and sub-entities.")
        extracted_data = {}

        from entities.registry import POLICY_ENTITY_VIEWSETS

        for entity_name, viewset_class in POLICY_ENTITY_VIEWSETS.items():
            viewset_instance = viewset_class()

            if entity_name == "okta_policy_profile_enrollment_apps" or entity_name == "okta_policy_rule_profile_enrollment":
                extracted_data[entity_name] = []
                for profile_enrollment in extracted_data.get("okta_policy_profile_enrollment", []):
                    policy_profile_enrollment_id = profile_enrollment["id"]
                    data, _, _ = viewset_instance.fetch_from_okta(policy_profile_enrollment_id, request=request)

                    extracted = viewset_instance.extract_data(data, policy_profile_enrollment_id)
                    if extracted:
                        extracted_data.setdefault(entity_name, []).extend(extracted)
                    else:
                        logger.info(f"No {entity_name} data extracted for Policy {policy_profile_enrollment_id}. Skipping.")

            elif entity_name == "okta_policy_rule_mfa":
                extracted_data[entity_name] = []
                for policy in extracted_data.get("okta_policy_mfa", []):
                    policy_id = policy["id"]
                    data, _, _ = viewset_instance.fetch_from_okta(policy_id, request=request)

                    extracted = viewset_instance.extract_data(data, policy_id)
                    if extracted:
                        extracted_data.setdefault(entity_name, []).extend(extracted)
                    else:
                        logger.info(f"No {entity_name} data extracted for Policy {policy_id}. Skipping.")

            elif entity_name == "okta_policy_rule_password":
                extracted_data[entity_name] = []
                for policy in extracted_data.get("okta_policy_password", []):
                    policy_id = policy["id"]
                    data, _, _ = viewset_instance.fetch_from_okta(policy_id, request=request)

                    extracted = viewset_instance.extract_data(data, policy_id)
                    if extracted:
                        extracted_data[entity_name].extend(extracted)
                    else:
                        logger.info(f"No {entity_name} data extracted for Policy {policy_id}. Skipping.")

            elif entity_name == "okta_policy_rule_signon":
                extracted_data[entity_name] = []
                for policy in extracted_data.get("okta_policy_signon", []):
                    policy_id = policy["id"]
                    data, _, _ = viewset_instance.fetch_from_okta(policy_id, request=request)

                    extracted = viewset_instance.extract_data(data, policy_id)
                    if extracted:
                        extracted_data[entity_name].extend(extracted)
                    else:
                        logger.info(f"No {entity_name} data extracted for Policy {policy_id}. Skipping.")
            else:
                data, status_code, rate_limit = viewset_instance.fetch_from_okta(request=request)
                extracted_data[entity_name] = viewset_instance.extract_data(data)

            logger.info(f"Extracted {len(extracted_data.get(entity_name, []))} records for {entity_name}.")

        extracted_data_cleaned = {
            entity: clean_entity_data(entity, data)
            for entity, data in extracted_data.items()
        }

        for entity_name, data in extracted_data_cleaned.items():
            viewset_instance = POLICY_ENTITY_VIEWSETS[entity_name]()
            viewset_instance.store_data(data, db_name)

        return extracted_data_cleaned
