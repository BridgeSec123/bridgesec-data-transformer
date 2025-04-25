import logging

from core.utils.entity_mapping import clean_entity_data
from entities.views.base_view import BaseEntityViewSet

logger = logging.getLogger(__name__)

class BasePolicyViewSet(BaseEntityViewSet):
    """
    Base ViewSet to handle fetching and storing both policies and Sub-Entities data dynamically.
    """

    def fetch_and_store_data(self, db_name):
        logger.info("Starting fetch and store process for policies and sub-entities.")
        extracted_data = {}

        from entities.registry import POLICY_ENTITY_VIEWSETS
        for entity_name, viewset_class in POLICY_ENTITY_VIEWSETS.items():
            viewset_instance = viewset_class()

            if entity_name == "okta_policy_profile_enrollment_apps":
                extracted_data[entity_name] = []
                for profile_enrollment in extracted_data.get("okta_policy_profile_enrollment", []):
                    policy_profile_enrollment_id = profile_enrollment["id"]
                    data, _, _ = viewset_instance.fetch_from_okta(policy_profile_enrollment_id)
                    
                    extracted = viewset_instance.extract_data(data, policy_profile_enrollment_id)
                    if extracted:  # Only add if not empty
                        extracted_data.setdefault(entity_name, []).extend(extracted)
                    else:
                        logger.info(f"No {entity_name} data extracted for POlicy {policy_profile_enrollment_id}. Skipping.")
            elif entity_name == "okta_policy_rule_mfa":
                extracted_data[entity_name] = []
                for policy in extracted_data.get("okta_policy_mfa", []):
                    policy_id = policy["id"]
                    data, _, _ = viewset_instance.fetch_from_okta(policy_id)
                    
                    extracted = viewset_instance.extract_data(data, policy_id)         
                    if extracted:  # Only add if not empty
                        extracted_data.setdefault(entity_name, []).extend(extracted)
                    else:
                        logger.info(f"No {entity_name} data extracted for POlicy {policy_id}. Skipping.")
            else:
                data, status_code, rate_limit = viewset_instance.fetch_from_okta()
                extracted_data[entity_name] = viewset_instance.extract_data(data)

        extracted_data_cleaned = {
            entity: clean_entity_data(entity, data)
            for entity, data in extracted_data.items()
        }

        logger.info(f"Extracted {len(extracted_data[entity_name])} records for {entity_name}.")

        for entity_name, data in extracted_data_cleaned.items():
            viewset_instance = POLICY_ENTITY_VIEWSETS[entity_name]()
            viewset_instance.store_data(data, db_name)

        return extracted_data_cleaned
