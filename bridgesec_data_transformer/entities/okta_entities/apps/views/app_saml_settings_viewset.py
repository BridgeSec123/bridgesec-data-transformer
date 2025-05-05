import logging

from entities.okta_entities.apps.views.apps_base_viewset import  BaseAppViewSet
from entities.okta_entities.apps.apps_models import (
    AppSAMLSettings,
)
from entities.okta_entities.apps.apps_serializers import (
    AppSAMLSettingsSerializer,
)

logger = logging.getLogger(__name__)

class AppSAMLSettingsViewSet(BaseAppViewSet):
    entity_type = "okta_app_saml_settings"
    serializer_class =  AppSAMLSettingsSerializer
    model = AppSAMLSettings
    
    def extract_data(self, okta_data):
        logger.info("Extracting data from Okta response")
        extracted_data = super().extract_data(okta_data)

        formatted_data = []
        
        for record in extracted_data:
            if record.get("signOnMode") == "SAML_2_0":
                formatted_record = {
                    "app_id": record.get("id", ""),
                    "settings": record.get("settings", {})
                }
                formatted_data.append(formatted_record)
        logger.info("Extracted and formatted %d Identity Provider records from Okta", len(formatted_data))
        
        return formatted_data