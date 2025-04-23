import logging

import requests
from core.utils.pagination import fetch_all_pages
from core.utils.rate_limit import handle_rate_limit, rate_limit_headers
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response

from entities.okta_entities.users.user_models import UserFactor
from entities.okta_entities.users.user_serializers import UserFactorSerializer
from entities.okta_entities.users.views.user_base_viewset import BaseUserViewSet

logger = logging.getLogger(__name__)

class UserFactorViewSet(BaseUserViewSet):
    okta_endpoint = "/api/v1/users/{user_id}/factors"
    entity_type = "user_factors"
    serializer_class = UserFactorSerializer
    model = UserFactor
    
    def fetch_from_okta(self, user_id):
        """
        Fetch group membership details for a specific group from Okta.
        
        :param group_id: The Okta Group ID for which to fetch membership data.
        :return: JSON response from Okta API.
        """
        if not user_id:
            logger.error("User ID is required to fetch memberships.")
            return []

        if not self.okta_endpoint:
            logger.error("Okta endpoint not defined")
            return {"error": "Okta endpoint not defined"}, 500

        okta_url = f"{settings.OKTA_API_URL}/{self.okta_endpoint.format(user_id=user_id)}"
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

    def extract_data(self, okta_data):
        extracted_data =super().extract_data(okta_data)
        formatted_data = []
        for factor in extracted_data:
            factor_dict = {
                "provider_id": factor.get("id"),
                "active": factor.get("status"),
            }
            formatted_data.append(factor_dict)
        return formatted_data
    
    def list(self, request, *args, **kwargs):
        """Retrieve all records from MongoDB and return serialized data."""
        start_date, end_date = super().list(request, *args, **kwargs)

        if not start_date or not end_date:
            user_types = self.model.objects()  # Fetch all documents using MongoEngine
            logger.info("Retrieved %d user records from MongoDB", len(user_types))

        else:
            user_types = self.filter_by_date(start_date, end_date)
            logger.info(f"Retrieved {len(user_types)} user types between {start_date} and {end_date}")

        user_types_data = []
        for user_type in user_types:
            user_type_data = {
                "name": user_type.name,
                "display_name": user_type.displayName,
                "description": user_type.description,
            } 

            user_types_data.append(user_type_data)
        logger.info(f"Returning {len(user_types_data)} user types.")
        return Response(user_types_data, status=status.HTTP_200_OK)