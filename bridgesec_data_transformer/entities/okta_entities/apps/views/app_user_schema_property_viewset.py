# import logging

# import requests
# from core.utils.rate_limit import handle_rate_limit, rate_limit_headers
# from django.conf import settings

# from entities.okta_entities.apps.apps_models import  AppUserSchemaProperty
# from entities.okta_entities.apps.apps_serializers import  AppUserSchemaPropertySerializer
# from entities.okta_entities.apps.views.apps_base_viewset import BaseAppViewSet

# logger = logging.getLogger(__name__)

# class AppUserSchemaPropertyViewSet(BaseAppViewSet):
#     okta_endpoint = "/api/v1/meta/schemas/apps/{appId}/default"
#     entity_type = "okta_app_user_schema_property"
#     serializer_class = AppUserSchemaPropertySerializer
#     model = AppUserSchemaProperty

#     def fetch_from_okta(self):
#         """
#         Fetch all Okta apps, then fetch user base schema properties for each app,
#         and group results by app_id.
#         """
#         base_url = settings.OKTA_API_URL
#         headers = {"Authorization": f"SSWS {settings.OKTA_API_TOKEN}"}

#         discovery_url = f"{base_url}/api/v1/apps"
#         response = requests.get(discovery_url, headers=headers)

#         if handle_rate_limit(response):
#             logger.warning("Rate limit hit while fetching app IDs.")
#             return {"error": "Rate limit hit."}, 429, rate_limit_headers(response)

#         if response.status_code != 200:
#             logger.error(f"Failed to fetch app list: {response.text}")
#             return {"error": f"Failed to fetch apps: {response.text}"}, response.status_code, rate_limit_headers(response)

#         apps = response.json()
#         users_data = []

#         logger.info(f"Found {len(apps)} apps. Fetching user base schema properties for each...")

#         for app in apps:
#             app_id = app.get("id")
#             if not app_id:
#                 logger.warning("App without ID found. Skipping.")
#                 continue

#             users_url = f"{base_url}/api/v1/meta/schemas/apps/{app_id}/default"
#             user_response = requests.get(users_url, headers=headers)

#             if handle_rate_limit(user_response):
#                 logger.warning(f"Rate limit hit while fetching user base schema for app {app_id}. Skipping.")
#                 continue

#             if user_response.status_code != 200:
#                 logger.warning(f"Failed to fetch user base schema for app {app_id}: {user_response.text}")
#                 continue

#             user_data = user_response.json()
#             logger.info(f"Fetched user base schema properties for app {app_id}.")

#             users_data.append({
#                 "app_id": app_id,
#                 "user": user_data
#             })

#         return users_data, 200, rate_limit_headers(response)

#     def extract_data(self, okta_data):
#         logger.info("Extracting data from Okta response")

#         formatted_data = []

#         for record in okta_data:
#             app_id = record.get("app_id")
#             user= record.get("user", {})
#             base = user.get("definitions", {}).get("base", {})
#             formatted_record = {
#                 "app_id": app_id,
#                 "index": user.get("name", ""),
#                 "title": user.get("title", ""),  
#                 "type": user.get("type", ""),
#                 "array_enum":record.get("array_enum", []),
#                 "array_one_of": record.get("array_one_of", []),
#                 "array_type": record.get("array_type", ""),
#                 "enum": record.get("enum", []),
#                 "description": record.get("description", ""),
#                 "external_name": record.get("external_name", ""),
#                 "external_namespace": record.get("external_namespace", ""),
#                 "master": base.get("properties", {}).get("userName", {}).get("master", {}).get("type", ""),
#                 "max_length": record.get("max_length", ""),
#                 "min_length": record.get("min_length", ""),
#                 "one_of": record.get("one_of", []),
#                 "permissions": user.get("permissions", ""),
#                 "required":True if base.get("required", "")[0] else False,
#                 "scope": record.get("scope", ""),
#                 "unique": record.get("unique", ""),
#                 "union": record.get("union", ""),
#                 "user_type":  user.get("userType", "default")
#             }
#             formatted_data.append(formatted_record)

#         logger.info("Final extracted %d app user base schema properties records after formatting and flattening", len(formatted_data))
#         return formatted_data
