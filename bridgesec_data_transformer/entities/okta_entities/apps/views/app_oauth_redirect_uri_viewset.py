import logging

import requests
from core.utils.pagination import fetch_all_pages
from core.utils.rate_limit import handle_rate_limit, rate_limit_headers
from django.conf import settings

from entities.okta_entities.apps.apps_models import AppOauthRedirectUri
from entities.okta_entities.apps.apps_serializers import (
    AppOauthRedirectUriSerializer,
)
from entities.okta_entities.apps.views.apps_base_viewset import BaseAppViewSet

logger = logging.getLogger(__name__)

class AppOauthRedirectUriViewSet(BaseAppViewSet):
    okta_endpoint = "/api/v1/apps/{app_id}"
    entity_type = "okta_apps_oauth_redirect_uri"
    serializer_class = AppOauthRedirectUriSerializer
    model =  AppOauthRedirectUri

    def fetch_from_okta(self):
        """
        Fetch all Okta apps, then extract redirect URIs from each app,
        replacing app_id with app_label.
        """
        base_url = settings.OKTA_API_URL
        headers = {"Authorization": f"SSWS {settings.OKTA_API_TOKEN}"}

        # Fetch all apps
        discovery_url = f"{base_url}/api/v1/apps"
        response = requests.get(discovery_url, headers=headers)

        if handle_rate_limit(response):
            return {"error": "Rate limit hit."}, 429, rate_limit_headers(response)

        if response.status_code != 200:
            return {"error": f"Failed to fetch apps: {response.text}"}, response.status_code, rate_limit_headers(response)

        apps = response.json()
        all_apps_data = []

        redirect_uri_data = []

        for app in apps:
            app_id = app.get("id")
            app_label = app.get("label", app_id)

            if not app_id:
                continue

            # Check if this app has OPENID_CONNECT signOnMode and redirect URIs
            if app.get("signOnMode") == "OPENID_CONNECT":
                uri = app.get("settings", {}).get("oauthClient", {}).get("redirect_uris", [])
                if uri:
                    redirect_uri_data.append({
                        "app_id": app_label,  # Store app_label instead of app_id
                        "uri": uri
                    })

        return redirect_uri_data, 200, rate_limit_headers(response)

    def extract_data(self, okta_data):
        """
        Extract and format redirect URI data, converting app_id to app_label.
        """
        extracted_data = super().extract_data(okta_data)
        formatted_data = []

        for record in extracted_data:
            if record.get("signOnMode") == "OPENID_CONNECT":
                uri = record.get("settings", {}).get("oauthClient", {}).get("redirect_uris", [])
                if uri:
                    # Use the app_label we added in fetch_from_okta
                    app_label = record.get("app_label", record.get("label", record.get("id")))
                    formatted_record = {
                        "app_id": app_label,  # Store app_label instead of app_id
                        "uri": uri
                    }
                    formatted_data.append(formatted_record)

        logger.info("Extracted and formatted %d Okta OAuth redirect URI records from Okta", len(formatted_data))
        return formatted_data
