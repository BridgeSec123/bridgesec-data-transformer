import logging

import requests
from core.utils.pagination import fetch_all_pages
from core.utils.rate_limit import handle_rate_limit, rate_limit_headers
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response

from entities.okta_entities.users.user_models import AdminRoleTargets
from entities.okta_entities.users.user_serializers import AdminRoleTargetsSerializer
from entities.okta_entities.users.views.user_base_viewset import BaseUserViewSet

logger = logging.getLogger(__name__)

class AdminRoleTargetsViewSet(BaseUserViewSet):
    okta_endpoint = "/api/v1/users/{user_id}/roles/{roleAssignmentId}/targets/catalog/apps"
    entity_type = "okta_admin_role_targets"
    serializer_class = AdminRoleTargetsSerializer
    model = AdminRoleTargets
    
    def fetch_from_okta(self, user_id, role_id):
        if not user_id:
            logger.error("User ID is required to fetch memberships.")
            return []

        if not self.okta_endpoint:
            logger.error("Okta endpoint not defined")
            return {"error": "Okta endpoint not defined"}, 500

        okta_url = f"{settings.OKTA_API_URL}/{self.okta_endpoint.format(user_id=user_id, roleAssignmentId=role_id)}"
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
                return all_data

            return response_data

    def extract_data(self, okta_data, user_id, role_type):
        extracted_data =super().extract_data(okta_data)
        formatted_data = []
        apps = []
        for record in extracted_data:
            app_name = record.get("name")
            if app_name:
                apps.append(app_name)

        formatted_data = [{
            "role_type": role_type,
            "user_id": user_id,
            "apps": apps,
            "groups": []  
        }]

        return formatted_data