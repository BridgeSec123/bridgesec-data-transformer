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

        extracted_rules = []
        for rule in okta_data:
            rule_entry = {
                "name": rule.get("name"),
                "status": rule.get("status"),
                "group_assignments": rule.get("groupAssignments"),
                "expression_type": rule.get("expressionType"),
                "expression_value": rule.get("expressionValue"),
                "remove_assigned_users": rule.get("removeAssignedUsers"),
                "users_excluded": rule.get("usersExcluded"),
            }
            extracted_rules.append(rule_entry)

        logger.info(f"Extracted {len(extracted_rules)} group rule entries.")
        return extracted_rules

    def list(self, request, *args, **kwargs):
        """Retrieve all records from MongoDB and return serialized data."""
        start_date, end_date = super().list(request, *args, **kwargs)

        if not start_date or not end_date:
            rules = self.model.objects()
            logger.info("Retrieved %d group rule records from MongoDB", len(rules))
        else:
            memberships = self.filter_by_date(start_date, end_date)      
            logger.info(f"Retrieved {len(memberships)} group rules between {start_date} and {end_date}")

        memberships_data = [
            {
                "group_id": membership.group_id,
                "user_id": membership.user_id,
                "user_email": membership.user_email,
            }
            for membership in memberships
        ]

        logger.info(f"Returning {len(memberships_data)} group rules.")
        return Response(memberships_data, status=status.HTTP_200_OK)