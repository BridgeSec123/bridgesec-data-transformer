import logging

from django.conf import settings
import requests

from core.utils.pagination import fetch_all_pages
from core.utils.rate_limit import handle_rate_limit, rate_limit_headers
from entities.okta_entities.groups.group_models import GroupSchemaProperty
from entities.okta_entities.groups.group_serializers import GroupSchemaPropertySerializer
from entities.okta_entities.groups.views.group_base_viewset import BaseGroupViewSet
from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger(__name__)

class GroupSchemaPropertyViewSet(BaseGroupViewSet):
    okta_endpoint = "/api/v1/meta/schemas/group/default"
    entity_type = "group_schemas"
    serializer_class = GroupSchemaPropertySerializer
    model = GroupSchemaProperty
    
    def list(self, request, *args, **kwargs):
        """Retrieve all records from MongoDB and return serialized data."""
        start_date, end_date = super().list(request, *args, **kwargs)

        if not start_date or not end_date:
            groups = self.model.objects()  # Fetch all documents using MongoEngine
            logger.info("Retrieved %d groups records from MongoDB", len(groups))

        else:
            groups = self.filter_by_date(start_date, end_date)
            logger.info(f"Retrieved {len(groups)} groups between {start_date} and {end_date}")

        groups_data = []
        for group in groups:
            group_data = {
                "name": group.name,
                "description": group.description,
            }
            if group.custom_profile_attributes:
                group_data["custom_profile_attributes"] = group.custom_profile_attributes

            groups_data.append(group_data)

        logger.info(f"Returning {len(groups_data)} groups.")
        return Response(groups_data, status=status.HTTP_200_OK)
    
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

            return [response_data], 200, rate_limit_headers(response)
    
    def extract_data(self, okta_data):
        logger.info("Extracting data from Okta response.")
        extracted_data = super().extract_data(okta_data)
        formatted_data = []
        
        for record in extracted_data:
            formatted_data.append(
                {
                    "index": record.get("title", ""),
                    "title": record.get("title", ""),
                    "type": record.get("type", ""),
                    "array_enum": record.get("arrayEnum", []),
                    "array_one_of": record.get("arrayOneOf", []),
                    "array_type": record.get("arrayType", ""),
                    "description": record.get("description", ""),
                    "enum": record.get("enum", []),
                    "external_name": record.get("externalName", ""),
                    "external_namespace": record.get("externalNamespace", ""),
                    "one_of": record.get("oneOf", []),
                    "permissions": record.get("permissions", []),
                    "required": record.get("required", False),
                    "master": record.get("definitions", "").get("base").get("properties").get("name").get("master", "").get("type", ""),
                    "master_override_priority": record.get("masterOverridePriority"),
                    "max_length": record.get("maxLength"),
                    "min_length": record.get("minLength"),
                    "scope": record.get("definitions", "").get("base").get("properties").get("name").get("scope", ""),
                }
            )
        return formatted_data