import logging

import requests
from core.utils.okta_helpers import get_okta_headers
from django.conf import settings
from entities.okta_entities.groups.group_models import GroupRule
from entities.okta_entities.groups.group_serializers import GroupRuleSerializer
from entities.okta_entities.groups.views.group_base_viewset import BaseGroupViewSet
from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger(__name__)

class GroupRuleViewSet(BaseGroupViewSet):
    """
    ViewSet to fetch and store group rule details from Okta.
    """
    okta_endpoint = "api/v1/groups/rules"
    entity_type = "group_rules"
    serializer_class = GroupRuleSerializer
    model = GroupRule

    def get_group_names_from_ids(self, group_ids, request=None):
        """
        Fetch group names by making API calls for each group ID.
        """
        if not group_ids:
            return []

        group_names = []
        headers = get_okta_headers(request)

        for group_id in group_ids:
            try:
                group_url = f"{self.okta_base_url}/api/v1/groups/{group_id}"
                response = requests.get(group_url, headers=headers)
                if response.status_code == 200:
                    group_data = response.json()
                    group_name = group_data.get("profile", {}).get("name") or group_data.get("name", "")
                    if group_name:
                        group_names.append(group_name)
                    else:
                        logger.warning(f"No name found for group ID {group_id}")
                        group_names.append(group_id)
                else:
                    logger.warning(f"Failed to fetch group details for ID {group_id}")
                    group_names.append(group_id)
            except Exception as e:
                logger.error(f"Error fetching group details for ID {group_id}: {e}")
                group_names.append(group_id)

        return group_names

    def extract_data(self, okta_data):
        """
        Extract and format group rule data from Okta response.
        """
        logger.info("Extracting group rule data from Okta response.")

        extracted_rules = []
        for rule in okta_data:
            if not isinstance(rule, dict):
                logger.warning(f"Skipping unexpected group rule item (expected dict, got {type(rule).__name__}): {rule!r}")
                continue
            conditions = rule.get("conditions", {})
            expressions= conditions.get("expression", {})
            people= conditions.get("people", {})
            groups_assignments = rule.get("actions", {}).get("assignUserToGroups", {})
            group_ids = groups_assignments.get("groupIds", [])
            # group_names = self.get_group_names_from_ids(group_ids)

            rule_entry = {
                "name": rule.get("name"),
                "group_rule_id": rule.get("id"),
                "status": rule.get("status"),
                "group_assignments": group_ids,
                "expression_type": expressions.get("type",""),
                "expression_value": expressions.get("value",""),
                "remove_assigned_users": rule.get("removeAssignedUsers",""),
                "users_excluded": people.get("users", {}).get("exclude", []),
            }
            extracted_rules.append(rule_entry)

        logger.info(f"Extracted {len(extracted_rules)} group rule entries.")
        return extracted_rules
