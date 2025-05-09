import logging

import requests
from core.utils.pagination import fetch_all_pages
from core.utils.rate_limit import handle_rate_limit, rate_limit_headers
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response

from entities.okta_entities.brands.brand_models import Brand
from entities.okta_entities.brands.brand_serializers import BrandSerializer
from entities.views.base_view import BaseEntityViewSet

logger = logging.getLogger(__name__)

class BrandEntityViewSet(BaseEntityViewSet):
    okta_endpoint = "api/v1/brands"
    entity_type = "brands"
    serializer_class = BrandSerializer
    model = Brand
    
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
        formatted_data = []
        for data in extracted_data:
            default_app = data.get("defaultApp")
            formatted_record = {
                "name": data.get("name"),
                "brand_id": data.get("id"),
                "agree_to_custom_privacy_policy": data.get("agreeToCustomPrivacyPolicy"),
                "custom_privacy_policy_url": data.get("customPrivacyPolicyUrl"),
                "default_app_app_instance_id": default_app.get("appInstanceId"),
                "default_app_app_link_name": default_app.get("appLinkName"),
                "default_app_classic_application_uri": default_app.get("classicApplicationUri"),
                "locale": data.get("locale"),
                "remove_powered_by_okta": data.get("removePoweredByOkta"),
            }
            formatted_data.append(formatted_record)
        
        logger.info(f"Extracted {len(formatted_data)} brands from Okta response")
        return formatted_data
    
    def fetch_and_store_data(self, db_name):
        """Fetch data from Okta and store in MongoDB."""
        try:
        # Step 1: Fetch data from Okta
            okta_response, status_code, headers = self.fetch_from_okta()
            logger.info("Fetched brand data from Okta")

            # Step 2: Extract and format data
            extracted_data = self.extract_data(okta_response)
            logger.info("Extracted %d brand records from Okta response", len(extracted_data))

            # Step 3: Store extracted data in MongoDB
            self.store_data(extracted_data, db_name=db_name)
            logger.info("Stored %d brand records in MongoDB database: %s", len(extracted_data), db_name)

            return {"brands": extracted_data}

        except Exception as e:
            logger.error("Error in fetch_and_store_data: %s", str(e), exc_info=True)
            return {
                "error": str(e),
                "message": "Failed to fetch and store brand data."
            }
