import logging
from datetime import datetime

import requests
from core.utils.entity_mapping import extract_entity_data
from core.utils.mongo_utils import ensure_mongo_connection, get_dynamic_db
from core.utils.pagination import fetch_all_pages
from core.utils.rate_limit import handle_rate_limit, rate_limit_headers
from django.conf import settings
from django.http import JsonResponse
from pymongo import MongoClient
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

logger = logging.getLogger(__name__)

class BaseEntityViewSet(viewsets.ModelViewSet):
    """Base viewset for Okta API integration."""
    
    queryset = None
    okta_endpoint = ""
    model = None
    serializer_class = None
    list_serializer_class = None
    entity_type = None
    http_method_names = ["get"]
    
    def get_queryset(self):
        """Ensure MongoDB connection before querying the database."""
        if hasattr(self, 'request'):
            # Block only schema generation requests, not actual API calls
            if "/swagger" in self.request.path:
                return self.model.objects.none()
            db_name = get_dynamic_db()
            ensure_mongo_connection(db_name)
            return self.model.objects.using(db_name).all()

        # Otherwise, return an empty queryset to prevent unnecessary DB creation
        return self.model.objects.none()
    
    def list(self, request, *args, **kwargs):
        """Retrieve all records from MongoDB and return the users data."""
        if not self.model or not self.serializer_class:
            logger.error("Model or serializer_class is not defined in UserViewSet.")
            return Response({"error": "Model or serializer_class not defined"}, status=status.HTTP_400_BAD_REQUEST)
        
        """Retrieve start and end date from query parameters."""
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        
        return start_date, end_date
    
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
        """
        Extract relevant data from Okta response using the mapping.
        """
        if not self.entity_type:
            logger.error("Entity type not defined")
            return JsonResponse({"error": "Entity type not defined"}, status=500)

        extracted_data = extract_entity_data(self.entity_type, okta_data)
        # logger.info(f"Extracted {len(extracted_data)} records for entity: {self.entity_type}")
        return extracted_data

    def store_data(self, extracted_data, db_name, batch_size=200):
        """
        Store the extracted data in a dynamically named MongoDB database.
        """
        # Test this code for inserting all data at one go.
        # logger.info(f"Storing {self.entity_type} data in MongoDB database: {db_name}")

        # if not extracted_data:
        #     return db_name  # No data to insert

        # # Convert extracted_data to a list of dictionaries (MongoDB documents)
        # data_list = [self.model(**data).to_mongo().to_dict() for data in extracted_data]

        # # Perform a bulk insert
        # self.model.objects.using(db_name).insert_many(data_list)
        
        # # This is first code for inserting data
        
        # logger.info(f"Storing {self.entity_type} data in MongoDB database: {db_name}")

        # for data in extracted_data:
        #     entity = self.model(**data)
        #     entity.save(using=db_name)

        # return db_name
        
        logger.info(f"Storing {self.entity_type} data in MongoDB database: {db_name}")

        if not extracted_data:
            logger.warning("No data found to store.")
            return db_name  # No data to insert

        ensure_mongo_connection(db_name) 
        
        SORT_FIELD_MAP = {
        # App entities - sorted by label
        "okta_app_oauth": "label",
        "okta_app_saml": "label",
        "okta_app_swa": "label",
        "okta_app_auto_login": "label",
        "okta_app_bookmark": "label",
        "okta_app_basic_auth": "label",
        "okta_app_secure_password_store": "label",
        "okta_app_shared_credentials": "label",
        "okta_app_three_field": "label",
        "apps": "label",

        # User entities - sorted by name or profile
        "okta_users": "profile.firstName",
        "okta_user": "profile.firstName",
        "user_admin_roles": "name",
        "user_factors": "id",
        "user_types": "name",
        "user_schema_properties": "name",
        "user_base_schema_properties": "name",
        "okta_user_group_memberships": "id",
        "okta_admin_role_targets": "id",

        # Group entities - sorted by name
        "okta_groups": "name",
        "okta_group": "name",
        "group_memberships": "id",
        "group_roles": "name",
        "group_rules": "name",
        "group_schemas": "name",
        "okta_group_owners": "id",

        # Policy entities - sorted by name
        "okta_policy_sign_on": "name",
        "okta_policy_mfa": "name",
        "okta_policy_password": "name",
        "okta_policy_profile_enrollment": "name",
        "okta_policy_profile_enrollment_apps": "name",
        "okta_policy_rule_signon": "name",
        "okta_policy_rule_mfa": "name",
        "okta_policy_rule_password": "name",
        "okta_policy_rule_profile_enrollment": "name",
        "okta_policy_rule_idp_discovery": "name",
        "okta_app_policy_sign_on": "name",
        "okta_app_signon_policy_rule": "name",

        # App-related entities - sorted by id or name
        "okta_app_users": "id",
        "okta_app_user_schema_property": "name",
        "okta_app_user_base_schema_property": "name",
        "okta_apps_group_assignment": "id",
        "okta_apps_group_assignments": "id",
        "okta_apps_oauth_redirect_uri": "id",
        "okta_apps_oauth_post_redirect_uri": "id",
        "okta_apps_oauth_api_scope": "name",
        "okta_app_oauth_role_assignment": "id",
        "apps_access_policy_assignment": "id",
        "okta_app_saml_settings": "id",

        # Auth Server entities - sorted by name or id
        "auth_servers": "name",
        "auth_servers_default": "name",
        "auth_trusted_servers": "name",
        "auth_server_policy": "name",
        "auth_server_policy_rules": "name",
        "auth_server_claims": "name",
        "auth_servers_claim_default": "name",
        "auth_server_scopes": "name",

        # Identity Provider entities - sorted by name
        "identity_providers": "name",
        "okta_idp_oidc": "name",
        "okta_idp_saml": "name",
        "okta_idp_social": "name",

        # Other entities - sorted by name or id
        "brands": "name",
        "okta_theme": "name",
        "okta_email_domain": "domain",
        "trusted_origins": "name",
        "network_zones": "name",
        "authenticators": "name",
        "okta_factors": "factorType",
        "threat_insights": "id",
        "inline_hooks": "name",
        "event_hooks": "name",
        "sms_templates": "name",
        "okta_captcha": "id",
        "okta_captcha_org_wide_settings": "id",
        "behavior": "name",
        "orgs": "id",
        "okta_role_subscription": "id",
        "okta_admin_role_custom": "name",
        "okta_resource_set": "name",
        "okta_link_definition": "name"
    }
        sort_field = SORT_FIELD_MAP.get(self.entity_type, "name")  # defaulacted_data dynamically
        sorted_data = sorted(extracted_data, key=lambda x: x.get(sort_field, "")) # Ensure the DB connection exists

        data_list = [self.model(**data).to_mongo().to_dict() for data in sorted_data]
        collection = self.model.objects.using(db_name)._collection
        # Process in batches to avoid MongoDB's document size limits
        for i in range(0, len(data_list), batch_size):
            batch = data_list[i : i + batch_size]  # Get a batch of `batch_size` records
            collection.insert_many(batch)  # Bulk insert

            logger.info(f"Inserted {len(batch)} records into {db_name}")

        return db_name
    
    @action(detail=False, methods=["get"], url_path="fetch")
    def fetch_data(self, request):
        """
        Fetch data from Okta, extract required fields, and store in MongoDB.
        """
        try:
            logger.info(f"Fetching {self.entity_type} data from Okta")
            okta_data, status_code, _ = self.fetch_from_okta()
            if status_code != 200:
                return Response(okta_data, status=status_code)

            extracted_data = self.extract_data(okta_data)
            logger.info(f"Extracted {len(extracted_data)} records for entity: {self.entity_type}")
            serializer = self.serializer_class(data=extracted_data, many=True)

            if serializer.is_valid():
                db_name = self.store_data(extracted_data)
                return Response({"message": f"Data stored in {db_name}"}, status=status.HTTP_201_CREATED)

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.exception(f"Error in fetching/storing {self.entity_type} data")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def filter_by_date(self, start_date, end_date):
        """Filters records based on timestamp inside versions array."""
        if not self.model:
            return []

        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d")
            end_date = datetime.strptime(end_date, "%Y-%m-%d")
            query = {
                "versions.timestamp": {
                    "$gte": start_date,
                    "$lte": end_date
                }
            }
            return list(self.model.objects(__raw__=query))
        except Exception as e:
            logger.error(f"Error filtering data: {str(e)}")
            return []

    # @action(detail=False, methods=["get"], url_path="fetch-stored-data")
    def fetch_stored_data(self, request):
        """
        Fetch stored data from MongoDB based on date and entity type.
        """
        date_str = request.query_params.get("date")
        if not date_str:
            return Response({"error": "Missing 'date' parameter"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            datetime.strptime(date_str, "%Y-%m-%d")

            mongo_client = MongoClient(settings.MONGO_URI)
            all_dbs = mongo_client.list_database_names()

            date_prefix = f"{settings.MONGO_DB_NAME}_{date_str}"
            matched_dbs = [db for db in all_dbs if db.startswith(date_prefix)]

            if not matched_dbs:
                return Response({"error": f"No database found for date {date_str}"}, status=status.HTTP_404_NOT_FOUND)

            latest_db = sorted(matched_dbs)[-1]

            ensure_mongo_connection(latest_db)

            data = list(self.model.objects.using(latest_db).all().as_pymongo())
            for record in data:
                record.pop("_id", None)

            return Response(data, status=status.HTTP_200_OK)

        except ValueError:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD"}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)