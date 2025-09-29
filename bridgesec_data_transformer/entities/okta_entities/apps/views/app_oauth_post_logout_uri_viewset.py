import logging

from entities.okta_entities.apps.apps_models import AppOauthPostRedirectUri
from entities.okta_entities.apps.apps_serializers import (
    AppOauthPostRedirectUriSerializer,
)
from entities.okta_entities.apps.views.apps_base_viewset import BaseAppViewSet

logger = logging.getLogger(__name__)

class AppOauthPostRedirectUriViewSet(BaseAppViewSet):  
    entity_type = "okta_apps_oauth_post_redirect_uri"
    serializer_class = AppOauthPostRedirectUriSerializer
    model =  AppOauthPostRedirectUri

    def extract_data(self, okta_data):
        extracted_data = super().extract_data(okta_data)
        formatted_data =[]
        for record in extracted_data:
            if record.get("signOnMode") == "OPENID_CONNECT":
                uri= record.get("settings", {}).get("oauthClient", {}).get("post_logout_redirect_uris", [])
                if uri:
                    formatted_record = {
                        "app_id": record.get("label"),
                        "uri": uri
                    }
                    logger.info("Extracted and formatted %d Okta OAuth API scope records from Okta", len(formatted_data))
                    formatted_data.append(formatted_record)
        return formatted_data
