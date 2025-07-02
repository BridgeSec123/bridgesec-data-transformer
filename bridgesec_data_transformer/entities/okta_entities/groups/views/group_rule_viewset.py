import logging

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

    def extract_data(self, okta_data):
        """
        Extract and format group rule data from Okta response.
        """
        logger.info("Extracting group rule data from Okta response.")
        extracted_data = super().extract_data(okta_data)

        extracted_rules = []
        for rule in extracted_data: 
            group_ids = rule.get("actions",{}).get("assignUserToGroups", {}).get("groupIds",[])
            conditions = rule.get("conditions", {})
            expression = conditions.get("expression", {})
            users_excluded = conditions.get("people",{}).get("users", {}).get("exclude", [])

            rule_entry = {
                "name": rule.get("name"),
                "status": rule.get("status"),
                "group_assignments": group_ids,
                "expression_type": expression.get("type", ""),
                "expression_value": expression.get("value", ""),
                "remove_assigned_users": rule.get("removeAssignedUsers"),
                "users_excluded": users_excluded,
            }
            extracted_rules.append(rule_entry)

        logger.info(f"Extracted {len(extracted_rules)} group rule entries.")
        return extracted_rules
