import copy
import json
import logging
import os
from datetime import datetime

import requests
# from core.authentication import OktaTokenAuthentication
from core.tasks.bulk_tasks import run_bulk_entity_task
from core.utils.collection_mapping import (ENTITY_ID_MAPPING,
                                           NON_EDITABLE_FIELDS,
                                           RESOURCE_COLLECTION_MAP)
from core.utils.db_utils import (ENTITIES_WITH_BUILDERS, extract_time,
                                 get_collection_diff, get_collection_name,
                                 get_latest_db)
from core.utils.jwt_utils import get_user_from_request
from core.utils.model_registry import MODEL_REGISTRY
from core.utils.mongo_utils import ensure_mongo_connection, get_dynamic_db
from core.utils.restore_utils import (extract_terraform_target_params,
                                      fetch_and_merge_restored_data,
                                      remove_metadata_fields,
                                      store_restored_data_with_metadata)
from core.utils.schema_extractor import get_ui_backend_mapping
from core.utils.serializer_registry import SERIALIZER_REGISTRY
from django.conf import settings
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from entities.registry import ENTITY_VIEWSETS
from entities.serializers.restore_serializer import RestoreDataSerializer
from entities.services.resouce_data_service import EntityDataService
from pymongo import MongoClient
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

logger = logging.getLogger(__name__)

mongo_client = settings.MONGO_CLIENT
server_url = settings.SERVER_URL


class BulkEntityViewSet(viewsets.ViewSet):
    authentication_classes = []
    permission_classes = []
    serializer_class = RestoreDataSerializer

    @swagger_auto_schema(
        operation_description="Fetch data from all registered entity APIs and store them in MongoDB",
        responses={201: openapi.Response("Data fetched and stored successfully")},
    )
    @action(detail=False, methods=["post"], url_path="bulk")
    def post(self, request):
        """
        Triggers a background task to fetch fresh data for all registered entities and store them in a dynamic MongoDB.
        """
        run_bulk_entity_task.delay()

        return Response(
            {"message": "Data fetch task triggered successfully"},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get"], url_path="fetch-stored-data")
    def fetch_stored_data(self, request):
        """
        Fetch stored data using mongoengine models.
        ensure_mongo_connection is required here.
        """
        date_str = request.query_params.get("date")
        entity_type = request.query_params.get("entity")

        if not date_str or not entity_type:
            return Response(
                {"error": "Missing 'date' or 'entity' parameter"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            datetime.strptime(date_str, "%Y-%m-%d")

            mongo_client = MongoClient(settings.MONGO_URI)
            latest_db = get_latest_db(mongo_client, date_str)
            if not latest_db:
                return Response(
                    {"error": f"No database found for date {date_str}"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            ensure_mongo_connection(latest_db)  # needed since using .objects()

            model_class = ENTITY_VIEWSETS.get(entity_type)
            if not model_class:
                return Response(
                    {"error": "Invalid entity type"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            viewset_instance = model_class()
            data = list(
                viewset_instance.model.objects.using(latest_db).all().as_pymongo()
            )
            for record in data:
                record.pop("_id", None)

            return Response(data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=["get"], url_path="list-databases")
    def list_databases(self, request):
        """
        List all dynamic DBs, optionally filter by date.
        """
        date_str = request.query_params.get("date")

        try:
            all_dbs = mongo_client.list_database_names()

            if date_str:
                try:
                    datetime.strptime(date_str, "%Y-%m-%d")
                    date_prefix = f"{settings.MONGO_DB_NAME}_{date_str}"
                    all_dbs = [db for db in all_dbs if db.startswith(date_prefix)]
                except ValueError:
                    return Response(
                        {"error": "Invalid date format. Use YYYY-MM-DD"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            db_dict = {extract_time(db): db for db in all_dbs if extract_time(db)}
            return Response(db_dict, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=["get"], url_path="resource-names")
    def get_resource_names(self, request):
        """
        Return available entity types or sub-entities.
        """
        try:
            entity_type = request.query_params.get("entity_type")

            if entity_type:
                entity_type = entity_type.title()
                sub_entities = RESOURCE_COLLECTION_MAP.get(entity_type)
                if not sub_entities:
                    return Response(
                        {"detail": f"No sub-entities found for '{entity_type}'"},
                        status=status.HTTP_404_NOT_FOUND,
                    )
                display_names = [value for entry in sub_entities for value in entry.keys()]
                return Response({"data": display_names}, status=status.HTTP_200_OK)

            return Response(
                {"data": sorted(RESOURCE_COLLECTION_MAP.keys())},
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(
        detail=False,
        methods=["get"],
        url_path=r"data/(?P<date_str>\d{4}-\d{2}-\d{2})/(?P<entity_name>[^/.]+)",
    )
    def get_resource_data(self, request, date_str, entity_name):
        """
        Fetch resource data and merge with restored changes if available.

        Flow:
        1. Fetch original data from source DB (Policy MFA with nested rules)
        2. Check for restored collections in today's DB
        3. If restored data exists for specific policy_id, merge it
        4. Remove metadata fields (restored_by, restored_from, restored_at)
        5. Return merged data with non_editable_fields
        """
        # Normalize entity name (remove extra spaces from URL encoding)
        entity_name = " ".join(entity_name.split())

        if not date_str or not entity_name:
            return Response(
                {"error": "Missing 'date' or 'entity_type' parameter"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Validate date format
            datetime.strptime(date_str, "%Y-%m-%d")

            # Step 1: Fetch original data (with nested arrays for builder entities like Policy MFA)
            service = EntityDataService()
            original_data = service.fetch(date_str, entity_name)
            logger.info(f"Fetched {len(original_data)} original records for {entity_name}")

            # Get collection metadata
            collection_name = get_collection_name(entity_name)
            id_field = ENTITY_ID_MAPPING.get(entity_name)

            if not collection_name or not id_field:
                # Missing configuration, return original data only
                logger.warning(f"Missing collection_name or id_field for {entity_name}")
                return Response({
                    "data": original_data,
                    "non_editable_fields": NON_EDITABLE_FIELDS.get(entity_name, [])
                }, status=status.HTTP_200_OK)

            # Step 2 & 3: Check today's DB for restored collections and merge
            today_str = datetime.now().strftime("%Y-%m-%d")
            db_name = get_latest_db(mongo_client, today_str)

            if db_name:
                db = mongo_client[db_name]
                logger.info(f"Checking for restored data in database: {db_name}")

                # Fetch and merge restored data (uses functions from restore_utils.py)
                # This handles:
                # - Checking if _okta_policy_mfa exists
                # - Fetching latest versions by policy_id
                # - Rebuilding nested arrays from _okta_policy_rule_mfa
                # - Merging restored changes with original data (field-level merge)
                original_data = fetch_and_merge_restored_data(
                    db, entity_name, collection_name, id_field, original_data
                )
                logger.info(f"Merge complete: {len(original_data)} records")
            else:
                logger.info(f"No database found for today ({today_str}), using original data only")

            # Step 4: Remove metadata fields (restored_by, restored_from, restored_at, _id)
            remove_metadata_fields(original_data)
            logger.info("Removed metadata fields from response")

            # Step 5: Return merged data with non_editable_fields
            non_editable_fields = NON_EDITABLE_FIELDS.get(entity_name, [])

            return Response({
                "data": original_data,
                "non_editable_fields": non_editable_fields
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error in get_resource_data: {str(e)}", exc_info=True)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    @swagger_auto_schema(
        method="post",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "data": openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_OBJECT))
            },
            required=["data"],
        ),
        responses={201: "Success", 400: "Bad Request"},
    )
    @action(
        detail=False,
        methods=["post"],
        url_path=r"restore/(?P<date_str>\d{4}-\d{2}-\d{2})/(?P<entity_name>[^/.]+)",
    )
    def restore_modified_data(self, request, date_str, entity_name):
        """
        Restore data into a new dynamic DB using pymongo only → no ensure_mongo_connection.
        """
        try:
            modified_data = request.data.get("data", [])
            if not isinstance(modified_data, list):
                return Response(
                    {"error": "Invalid data format. 'data' must be a list"},
                    status=400,
                )

            # Validate data before storing in MongoDB
            # serializer_class = SERIALIZER_REGISTRY.get(entity_name)
            # if serializer_class:
            #     validation_errors = []
            #     for index, record in enumerate(modified_data):
            #         serializer = serializer_class(data=record)
            #         if not serializer.is_valid():
            #             validation_errors.append({
            #                 "record_index": index,
            #                 "record_data": record,
            #                 "errors": serializer.errors
            #             })

            #     if validation_errors:
            #         return Response(
            #             {
            #                 "error": "Validation failed for one or more records",
            #                 "validation_errors": validation_errors,
            #                 "total_errors": len(validation_errors),
            #                 "total_records": len(modified_data)
            #             },
            #             status=status.HTTP_400_BAD_REQUEST,
            #         )
            # else:
            #     logger.warning(f"No serializer found for entity '{entity_name}'. Skipping validation.")

            # resolve collection name
            collection_name = get_collection_name(entity_name)
            if not collection_name:
                return Response(
                    {
                        "message": f"Entity type '{entity_name}' not found in resource map",
                        "data": [],
                    },
                    status=status.HTTP_200_OK,
                )

            source_db_name = get_latest_db(mongo_client, date_str)
            if not source_db_name:
                return Response(
                    {"message": f"No source DB found for date {date_str}"},
                    status=404,
                )

            today_str = datetime.now().strftime("%Y-%m-%d")
            current_db_name = get_latest_db(mongo_client, today_str)

            if not current_db_name:
                current_db_name = get_dynamic_db()
                logger.info(f"No database found for today. Created new database: {current_db_name}")

            current_db = mongo_client[current_db_name]

            # Clean up _id fields
            for doc in modified_data:
                doc.pop("_id", None)

            # Store restored data (handles both simple and nested entities)
            data_for_storage = copy.deepcopy(modified_data)
            restored_by = get_user_from_request(request)

            stored_data = store_restored_data_with_metadata(
                current_db, entity_name, collection_name,
                data_for_storage, restored_by, source_db_name
            )

            # Extract target parameters for Terraform API
            # Uses original data (with nested arrays intact) to extract all IDs
            params = extract_terraform_target_params(collection_name, modified_data)

            # Send data to Terraform API
            tf_response = requests.post(
                f"{server_url}/api/",
                params=params,
                json={"data": modified_data},
                headers={"Content-Type": "application/json"},
            )

            try:
                tf_data = tf_response.json()
            except Exception:
                tf_data = {"message": "Unknown response from TF repo"}

            tf_message = tf_data.get("message", "No message returned")

            return Response(
                {
                    "tf_message": tf_message,
                    "message": "Modified data restored successfully.",
                    "restored_db": current_db_name,
                    "collection": f"_{collection_name}",
                    "record_count": len(modified_data),
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": str(e)}, status=500)

    @swagger_auto_schema(
        operation_description="Get entity schema for dynamic form generation in frontend",
        responses={
            200: openapi.Response("Entity schema with field definitions"),
            404: "Entity not found"
        }
    )
    @action(
        detail=False,
        methods=["get"],
        url_path=r"entity-schema/(?P<entity_name>[^/.]+)"
    )
    def get_entity_schema(self, request, entity_name=None):
        """
        Return simple UI to backend field mapping.
        Frontend uses this to dynamically build forms with UI-friendly field names.
        Returns format: {"App Id": "app_id", "Label": "label", ...}
        """
        try:
            # Get model class from registry
            model_class = MODEL_REGISTRY.get(entity_name)
            if not model_class:
                return Response({
                    "error": f"Entity '{entity_name}' not found",
                    "available_entities": sorted(MODEL_REGISTRY.keys())
                }, status=status.HTTP_404_NOT_FOUND)

            # Get simple UI to backend mapping
            mapping = get_ui_backend_mapping(model_class)

            # Add non-editable fields configuration to response
            non_editable_fields = NON_EDITABLE_FIELDS.get(entity_name, [])

            return Response({
                "schema": mapping,
                "non_editable_fields": non_editable_fields
            }, status=status.HTTP_200_OK)

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                "date1",
                openapi.IN_QUERY,
                description="First date in YYYY-MM-DD format",
                type=openapi.TYPE_STRING,
                required=True,
            ),
            openapi.Parameter(
                "date2",
                openapi.IN_QUERY,
                description="Second date in YYYY-MM-DD format",
                type=openapi.TYPE_STRING,
                required=True,
            ),
        ]
    )
    @action(
        detail=False,
        methods=["get"],
        url_path=r"diff-collections/(?P<entity_name>[^/.]+)",
    )
    def diff_collections(self, request, entity_name=None):
        """
        Compare two collection snapshots by date.
        """
        try:
            # Get query parameters
            date1 = request.query_params.get("date1")
            date2 = request.query_params.get("date2")

            # Validation
            if not entity_name:
                return Response(
                    {"error": "Path parameter 'entity_name' is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not date1 or not date2:
                return Response(
                    {"error": "Query parameters 'date1' and 'date2' are required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if entity_name not in ENTITY_ID_MAPPING:
                return Response(
                    {
                        "error": f"Entity '{entity_name}' not supported",
                        "available_entities": sorted(ENTITY_ID_MAPPING.keys())
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Validate date formats
            try:
                datetime.strptime(date1, "%Y-%m-%d")
                datetime.strptime(date2, "%Y-%m-%d")
            except ValueError:
                return Response(
                    {"error": "Invalid date format. Use YYYY-MM-DD"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get ID field for this entity
            id_field = ENTITY_ID_MAPPING[entity_name]

            # Use EntityDataService to get rebuilt data with nested arrays
            service = EntityDataService()
            old_docs = service.fetch(date1, entity_name)
            new_docs = service.fetch(date2, entity_name)

            if not old_docs and not new_docs:
                return Response(
                    {
                        "error": f"No data found for entity '{entity_name}' on either date",
                        "date1": date1,
                        "date2": date2
                    },
                    status=status.HTTP_404_NOT_FOUND
                )

            # Get structured diff with nested array comparison for entities with builders
            diff_result = get_collection_diff(
                old_docs,
                new_docs,
                id_field,
                entity_name=entity_name,
                date1=date1,
                date2=date2
            )

            # Add non-editable fields configuration to response
            non_editable_fields = NON_EDITABLE_FIELDS.get(entity_name, [])
            diff_result["non_editable_fields"] = non_editable_fields

            return Response(diff_result, status=status.HTTP_200_OK)

        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.error(f"Error in diff_collections: {str(e)}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# db_name = get_dynamic_db()
#         # Loop through all registered entity viewsets dynamically
#         for entity_name, viewset_class in ENTITY_VIEWSETS.items():
#             viewset_instance = viewset_class()

#         # Fetch and extract data using the base class methods
#         extracted_data = viewset_instance.fetch_and_store_data(db_name)
#         if not extracted_data: # If no data returned
#             return Response(
#                 {"error": f"Failed to fetch {entity_name} data"},
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR
#             )
#         # Setup output directory
#         output_dir = os.path.join(settings.BASE_DIR, "output", db_name)
#         os.makedirs(output_dir, exist_ok=True)

#         for sub_entity_name, sub_entity_data in extracted_data.items():
#             file_name = f"{sub_entity_name}.json"
#             file_path = os.path.join(output_dir, file_name)

#         with open(file_path, "w", encoding="utf-8") as f:
#             json.dump(sub_entity_data, f, ensure_ascii=False, indent=4)