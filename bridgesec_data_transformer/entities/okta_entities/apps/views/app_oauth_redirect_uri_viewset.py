import logging

from entities.okta_entities.apps.apps_models import AppOauthRedirectUri
from entities.okta_entities.apps.apps_serializers import (
    AppOauthRedirectUriSerializer,
)
from entities.okta_entities.apps.views.apps_base_viewset import BaseAppViewSet

logger = logging.getLogger(__name__)

class AppOauthRedirectUriViewSet(BaseAppViewSet):  
    entity_type = "okta_apps_oauth_redirect_uri"
    serializer_class = AppOauthRedirectUriSerializer
    model =  AppOauthRedirectUri

    def extract_data(self, okta_data):
        extracted_data = super().extract_data(okta_data)
        formatted_data =[]
        for record in extracted_data:
            if record.get("signOnMode") == "OPENID_CONNECT":
                uri= record.get("settings", {}).get("oauthClient", {}).get("redirect_uris", [])
                if uri:
                    formatted_record = {
                        "app_id": record.get("id"),
                        "uri": uri
                    }
                    logger.info("Extracted and formatted %d Okta OAuth API scope records from Okta", len(formatted_data))
                    formatted_data.append(formatted_record)
        return formatted_data
