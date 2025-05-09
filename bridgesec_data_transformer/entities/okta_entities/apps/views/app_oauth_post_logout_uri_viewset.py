import logging
import requests

from django.conf import settings
from core.utils.pagination import fetch_all_pages
from core.utils.rate_limit import handle_rate_limit, rate_limit_headers



from entities.okta_entities.apps.views.apps_base_viewset import BaseAppViewSet
from entities.okta_entities.apps.apps_models import AppOauthPostRedirectUri
from entities.okta_entities.apps.apps_serializers import AppOauthPostRedirectUriSerializer
logger = logging.getLogger(__name__)


class AppOauthPostRedirectUriViewSet(BaseAppViewSet):  
    entity_type = "okta_apps_oauth_post_redirect_uri"
    serializer_class = AppOauthPostRedirectUriSerializer
    model =  AppOauthPostRedirectUri

    def fetch_from_okta(self):
        """Fetch data from Okta API dynamically."""
        if not self.okta_endpoint:
            logger.error("Okta endpoint not defined")
            return {"error": "Okta endpoint not defined"}, 500

        okta_url = f"{settings.OKTA_API_URL}/{self.okta_endpoint}"
        headers = {"Authorization": f"SSWS {settings.OKTA_API_TOKEN}"}
        
        logger.info(f"Fetching data from Okta endpoint: {self.okta_endpoint}")
        
        while True:  # Keep retrying if rate limited
            response = requests.get(okta_url, headers=headers)

            if handle_rate_limit(response):  # Handle rate limit
                logger.warning("Rate limit reached. Retrying...")
                continue  # Retry after waiting

            if response.status_code != 200:
                logger.error(f"Failed to fetch data from Okta: {response.text}")
                return {"error": f"Failed to fetch data from Okta API: {response.text}"}, response.status_code, rate_limit_headers(response)

            response_data = response.json()
            logger.info(f"Successfully fetched data from Okta ({len(response_data)} records)")
            
            # Check if pagination is needed
            next_url = response.links.get("next", {}).get("url")
            if next_url:
                all_data = fetch_all_pages(okta_url, headers)
                return all_data, 200, rate_limit_headers(response)

            return response_data, 200, rate_limit_headers(response)


    def extract_data(self, okta_data):
        extracted_data = super().extract_data(okta_data)
        formatted_data =[]
        for record in extracted_data:
            if record.get("signOnMode") == "OPENID_CONNECT":
                uri= record.get("settings", {}).get("oauthClient", {}).get("post_logout_redirect_uris", [])
                if uri:
                    formatted_record = {
                        "app_id": record.get("id"),
                        "uri": uri
                    }
                    logger.info("Extracted and formatted %d Okta OAuth API scope records from Okta", len(formatted_data))
                    formatted_data.append(formatted_record)
        return formatted_data
         
        
      


        