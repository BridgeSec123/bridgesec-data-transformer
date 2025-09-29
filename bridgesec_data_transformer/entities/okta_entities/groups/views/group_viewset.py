import logging

from entities.okta_entities.groups.group_models import Group
from entities.okta_entities.groups.group_serializers import GroupSerializer
from entities.okta_entities.groups.views.group_base_viewset import BaseGroupViewSet
from entities.entity_filters import should_skip_group_extraction
logger = logging.getLogger(__name__)

class GroupEntityViewSet(BaseGroupViewSet):
    okta_endpoint = "/api/v1/groups"
    entity_type = "okta_groups"
    serializer_class = GroupSerializer
    model = Group
    
    def extract_data(self, okta_data):
        logger.info("Extracting data from Okta response.")
        extracted_data = super().extract_data(okta_data)

        # Flatten the data by removing the "profile" key
        formatted_data = []
        for record in extracted_data:
            if "profile" in record:
                profile = record["profile"]
                group_name = profile.get("name", "")

                # Check if this group should be excluded
                if should_skip_group_extraction(group_name):
                    logger.info(f"Skipping group extraction for name: {group_name}")
                    continue

                # changes here
                modified_profile = {
                    "group_id": record.get("id"),
                    "name": group_name,
                    "description": profile.get("description", ""),
                }
                scopes = profile.get("scopes", [])
                if scopes:
                    modified_profile["custom_profile_attributes"] = {"scopes": scopes}
                formatted_data.append(modified_profile)
                
        logger.info(f"Extracted and formatted {len(formatted_data)} group records from Okta.")
        return formatted_data