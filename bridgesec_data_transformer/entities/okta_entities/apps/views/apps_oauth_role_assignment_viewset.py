import logging

from entities.okta_entities.apps.views.apps_base_viewset import BaseAppViewSet
from entities.okta_entities.apps.apps_models import AppOuthRoleAssignment
from entities.okta_entities.apps.apps_serializers import AppOuthRoleAssignmentSerializer

logger = logging.getLogger(__name__)

class AppOauthRoleAssignmentViewSet(BaseAppViewSet):
    okta_endpoint = "/oauth2/v1/clients/{client_id}/roles"
    entity_type = "app_oauth_role_assignment"
    serializer_class = AppOuthRoleAssignmentSerializer
    model =  AppOuthRoleAssignment
        
       
    def extract_data(self, okta_data):
            """
            Override to format the user data by removing the "profile" key.
            """
            logger.info("Extracting data from Okta response")
            extracted_data = super().extract_data(okta_data)

            formatted_data = []
            # allowed_fields = set(User._fields.keys())

            for record in extracted_data:
            
                formatted_record = {
                    "client_id": record.get("client_id", ""),
                    "type": record.get("type", ""),
                    "resource_set": record.get("resource_set", ""),
                    "role":record.get("role", "")
                }
                formatted_data.append(formatted_record)

            logger.info("Final extracted %d user records after formatting and filtering", len(formatted_data))
            return formatted_data

        