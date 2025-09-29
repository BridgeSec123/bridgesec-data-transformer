import logging

import requests
from core.utils.pagination import fetch_all_pages
from core.utils.rate_limit import handle_rate_limit, rate_limit_headers
from django.conf import settings

from entities.okta_entities.apps.apps_models import AppOauthApiScope
from entities.okta_entities.apps.apps_serializers import AppOauthApiScopeSerializer
from entities.okta_entities.apps.views.apps_base_viewset import BaseAppViewSet

logger = logging.getLogger(__name__)

class AppOauthApiScopeViewSet(BaseAppViewSet):  
    okta_endpoint = "/api/v1/apps/{app_id}/grants"
    entity_type = "okta_apps_oauth_api_scope"
    serializer_class =  AppOauthApiScopeSerializer
    model =  AppOauthApiScope

    def fetch_from_okta(self, app_id):
        """
        Fetch data from Okta API dynamically.
        Convert app_id to app_label for consistent naming.
        """
        if not self.okta_endpoint:
            logger.error("Okta endpoint not defined")
            return {"error": "Okta endpoint not defined"}, 500

        base_url = settings.OKTA_API_URL
        headers = {"Authorization": f"SSWS {settings.OKTA_API_TOKEN}"}

        # First, get app label from app_id
        app_url = f"{base_url}/api/v1/apps/{app_id}"
        app_response = requests.get(app_url, headers=headers)

        app_label = app_id  # fallback to app_id
        if app_response.status_code == 200:
            app_data = app_response.json()
            app_label = app_data.get("label", app_id)
        else:
            logger.warning(f"Could not fetch app details for {app_id}, using app_id as fallback")

        okta_url = f"{base_url}/{self.okta_endpoint.format(app_id=app_id)}"

        logger.info(f"Fetching data from Okta endpoint: {self.okta_endpoint}")

        while True:  # Keep retrying if rate limited
            response = requests.get(okta_url, headers=headers)

            if handle_rate_limit(response):  # Handle rate limit
                logger.warning("Rate limit reached. Retrying...")
                continue  # Retry after waiting

            if response.status_code != 200:
                logger.error(f"Failed to fetch data from Okta: {response.text}")
                return {"error": f"Failed to fetch data from Okta API: {response.text}"}, response.status_code, rate_limit_headers(response), app_label

            response_data = response.json()
            logger.info(f"Successfully fetched data from Okta ({len(response_data)} records)")

            # Check if pagination is needed
            next_url = response.links.get("next", {}).get("url")
            if next_url:
                all_data = fetch_all_pages(okta_url, headers)
                return all_data, 200, rate_limit_headers(response), app_label

            return response_data, 200, rate_limit_headers(response), app_label

    def extract_data(self, okta_data, app_label):
        """
        Extract and format data, converting IDs to names where possible.
        app_label is now the app label instead of app_id.
        """
        extracted_data = super().extract_data(okta_data)
        scopes = []
        issuer = None
        

        for record in extracted_data:
            if issuer is None:
                issuer = record.get("issuer", "")

            scope_id = record.get("scopeId")
            if scope_id:
                scopes.append(scope_id)

        if issuer and scopes:
            formatted_data = [{
                "app_id": app_label,  # Now stores app_label instead of app_id
                "issuer": issuer,
                "scopes": scopes
            }]
            logger.info("Extracted and formatted %d Okta OAuth API scope records from Okta", len(formatted_data))
            return formatted_data

        logger.warning("No valid issuer or scopes found for app_label %s", app_label)
        return []

  