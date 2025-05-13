import logging

from entities.okta_entities.groups.group_models import Group
from entities.okta_entities.groups.group_serializers import GroupSerializer
from entities.okta_entities.groups.views.group_base_viewset import BaseGroupViewSet
logger = logging.getLogger(__name__)

class GroupEntityViewSet(BaseGroupViewSet):
    okta_endpoint = "/api/v1/groups"
    entity_type = "groups"
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
                # changes here
                modified_profile = {
                    "group_id": record.get("id"),
                    "name": profile.get("name", ""),
                    "description": profile.get("description", ""),
                }
                scopes = profile.get("scopes", [])
                if scopes:
                    modified_profile["custom_profile_attributes"] = {"scopes": scopes}
                formatted_data.append(modified_profile)
                
        logger.info(f"Extracted and formatted {len(formatted_data)} group records from Okta.")
        return formatted_data