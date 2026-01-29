import copy
import json
import logging
import os
from datetime import datetime

import requests
from core.authentication import CustomJWTAuthentication
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
from core.utils.nested_mapping import NESTED_FIELD_COLLECTIONS
from core.utils.okta_helpers import get_okta_headers
from core.utils.restore_utils import (extract_terraform_target_params,
                                      fetch_and_merge_restored_data,
                                      remove_metadata_fields,
                                      store_restored_data_with_metadata,
                                      store_created_data,
                                      store_deleted_data_with_metadata,
                                      update_deletion_status,
                                      filter_deleted_records_from_state,
                                      handle_nested_deletion,
                                      validate_deletion_safety)
from core.utils.schema_extractor import get_ui_backend_mapping
from core.utils.serializer_registry import SERIALIZER_REGISTRY
from django.conf import settings
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from entities.registry import ENTITY_VIEWSETS
from core.utils.collection_mapping import ENTITY_ID_MAPPING
from entities.serializers.restore_serializer import RestoreDataSerializer
from entities.services.resouce_data_service import EntityDataService
from pymongo import MongoClient
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.utils import fieldfetch
from core.utils import mapping_handlers
logger = logging.getLogger(__name__)

mongo_client = settings.MONGO_CLIENT
server_url = settings.SERVER_URL


class BulkEntityViewSet(viewsets.ViewSet):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
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
        # Get Okta access token and granted scopes from session to pass to background task
        okta_access_token = None
        okta_granted_scopes = []
        if hasattr(request, 'session'):
            okta_access_token = request.session.get('okta_access_token')
            okta_granted_scopes = request.session.get('okta_granted_scopes', [])

        # Pass access token and scopes to Celery task for Bearer token authentication
        run_bulk_entity_task.delay(
            okta_access_token=okta_access_token,
            okta_granted_scopes=okta_granted_scopes
        )

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
        manual_parameters=[
            openapi.Parameter(
                name="operation_type",
                in_=openapi.IN_QUERY,
                description="Operation type: 'delete' to delete resources, omit for restore/create operations",
                type=openapi.TYPE_STRING,
                required=False,
                enum=["delete"],
            )
        ],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "data": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    description="Array of resource objects. For delete operations, only ID field is required.",
                    items=openapi.Items(type=openapi.TYPE_OBJECT)
                )
            },
            required=["data"],
        ),
        responses={
            201: openapi.Response(
                description="Success",
                examples={
                    "application/json": {
                        "message": "Operations completed: 1 deleted",
                        "operations": {"deleted": 1, "restored": 0, "created": 0},
                        "tf_message": "Successfully deleted 1 resource(s) from Okta"
                    }
                }
            ),
            400: "Bad Request"
        },
    )
    @action(
        detail=False,
        methods=["post"],
        url_path=r"restore/(?P<date_str>\d{4}-\d{2}-\d{2})/(?P<entity_name>[^/.]+)",
    )

    def restore_modified_data(self, request, date_str, entity_name):
        """
        Restore data into a new dynamic DB using pymongo only → no ensure_mongo_connection.

        Query Parameters:
            - operation_type: "delete", "restore", or "create" (optional)
                If "delete", all records in body are treated as deletion targets
        """
        try:
            modified_data = request.data.get("data", [])
            if not isinstance(modified_data, list):
                return Response(
                    {"error": "Invalid data format. 'data' must be a list"},
                    status=400,
                )

            # Get operation_type from query parameters
            operation_type = request.query_params.get("operation_type")
            logger.info(f"Operation type from query param: {operation_type}")

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
            source_db = mongo_client[source_db_name]

            # Get ID field for this entity
            id_field = ENTITY_ID_MAPPING.get(entity_name)
            if not id_field:
                return Response(
                    {"error": f"Entity '{entity_name}' missing ID field configuration"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            # Separate records by operation type
            # If operation_type query param is "delete", treat ALL records as deletions
            deleted_records = []
            restore_records = []
            create_records = []

            if operation_type == "delete":
                # All records in body are deletion targets
                for doc in modified_data:
                    has_id = doc.get(id_field) is not None
                    if not has_id:
                        return Response(
                            {"error": f"Deletion requires valid ID field '{id_field}' in all records"},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    deleted_records.append(doc)
                logger.info(f"Delete operation: {len(deleted_records)} records marked for deletion")

            else:
                # Auto-detect operation based on presence of ID field
                for doc in modified_data:
                    has_id = doc.get(id_field) is not None

                    if has_id:
                        restore_records.append(doc)
                    else:
                        create_records.append(doc)
                logger.info(f"Auto-detected: {len(restore_records)} restored, {len(create_records)} created")

            logger.info(f"Operation counts: {len(deleted_records)} deleted, {len(restore_records)} restored, {len(create_records)} created")

            # Initialize variables for deletion tracking
            deleted_ids_list = []
            cascade_info = {}

            # Process deletion operations
            if deleted_records:
                logger.info(f"Processing {len(deleted_records)} deletion(s)")

                # Validate deletion safety
                errors = validate_deletion_safety(source_db, entity_name, collection_name, deleted_records)
                if errors:
                    return Response(
                        {"error": "Deletion validation failed", "details": errors},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # Fetch complete records from source DB for each deleted record
                complete_deleted_records = []
                for doc in deleted_records:
                    record_id = doc.get(id_field)
                    if not mapping_handlers.is_mapped_entity(collection_name):
                        complete_record = fieldfetch.get_collection(source_db, collection_name, doc)
                    else:
                        complete_record = fieldfetch.get_mapped_collection(source_db, collection_name, doc)

                    if complete_record:
                        complete_deleted_records.append(complete_record)

                logger.info(f"Fetched {len(complete_deleted_records)} complete records for deletion")

                # Store deleted records with metadata in "deletion_pending" status
                # This allows us to track the deletion attempt before Terraform runs
                restored_by = get_user_from_request(request)
                store_deleted_data_with_metadata(
                    current_db, entity_name, collection_name,
                    complete_deleted_records, restored_by, source_db_name,
                    operation_type="deletion_pending"  # PENDING status before Terraform
                )

                # Handle cascade deletion for nested entities (also with "deletion_pending" status)
                deleted_ids_list, cascade_info = handle_nested_deletion(
                    current_db, entity_name, complete_deleted_records,
                    restored_by, source_db_name
                )

                logger.info(f"Cascade deletion complete: {len(deleted_ids_list)} total IDs marked as deletion_pending")

            # Process restore operations
            if restore_records:
                logger.info(f"Processing {len(restore_records)} restore(s)")
                if not mapping_handlers.is_mapped_entity(collection_name):
                    for i, doc in enumerate(restore_records):
                        new_data = fieldfetch.get_collection(source_db, collection_name, doc)
                        restore_records[i] = new_data
                else:
                    for i, doc in enumerate(restore_records):
                        data = fieldfetch.get_mapped_collection(source_db, collection_name, doc)
                        restore_records[i] = data

            # Process create operations
            if create_records:
                logger.info(f"Processing {len(create_records)} creation(s)")
                for i, doc in enumerate(create_records):
                    create_records[i] = fieldfetch.transform_data(collection_name, doc)

            # Store restored and created data (deleted data was already stored above)
            restored_by = get_user_from_request(request)

            if restore_records:
                data_for_storage = copy.deepcopy(restore_records)
                store_restored_data_with_metadata(
                    current_db, entity_name, collection_name,
                    data_for_storage, restored_by, source_db_name
                )
                logger.info(f"Stored {len(restore_records)} restored records")

            if create_records:
                data_for_storage = copy.deepcopy(create_records)
                store_created_data(
                    current_db, entity_name, collection_name,
                    data_for_storage,
                )
                logger.info(f"Stored {len(create_records)} created records")

            # CRITICAL: Fetch ALL records from source DB and merge with restored/created data
            # This ensures Terraform receives complete state (not just modified records)
            # to prevent unintended resource deletion

            logger.info("=" * 80)
            logger.info("MERGING COLLECTIONS FOR TERRAFORM")
            logger.info("=" * 80)

            # Step 1: Fetch ALL original data from source DB snapshot
            service = EntityDataService()
            original_data = service.fetch(date_str, entity_name)
            logger.info(f"Step 1: Fetched {len(original_data)} original records from source DB ({source_db_name})")

            # Step 2: Merge original data with restored data from today's DB
            # This handles both simple entities and nested entities (with builders)
            # Note: fetch_and_merge_restored_data now filters out deleted records automatically
            merged_data = fetch_and_merge_restored_data(
                current_db, entity_name, collection_name, id_field, original_data
            )
            logger.info(f"Step 2: Merged to {len(merged_data)} total records (original + restored, deleted filtered)")

            # Step 3: Add newly created records (those without IDs in original data)
            # Created records only exist in restored collection with operation_type="created"
            restored_collection = current_db[f"_{collection_name}"]
            created_records_from_db = list(restored_collection.find(
                {"operation_type": "created"},
                {"_id": 0}
            ))

            if created_records_from_db:
                logger.info(f"Step 3: Found {len(created_records_from_db)} newly created records")

                # For created records with nested data, rebuild nested arrays
                nested_mapping = NESTED_FIELD_COLLECTIONS.get(entity_name)
                if nested_mapping:
                    # Rebuild nested arrays for created records
                    from core.utils.restore_utils import rebuild_restored_data_with_nested_arrays

                    # Get created records with nested arrays rebuilt
                    for created_record in created_records_from_db:
                        unique_id = created_record.get("unique_id")
                        if unique_id:
                            # Fetch nested data for this created record
                            for nested_field, nested_coll_name in nested_mapping.items():
                                nested_coll = f"_{nested_coll_name}"
                                if nested_coll in current_db.list_collection_names():
                                    nested_data = list(current_db[nested_coll].find(
                                        {"unique_id": unique_id, "operation_type": {"$ne": "deleted"}},
                                        {"_id": 0}
                                    ))
                                    created_record[nested_field] = nested_data
                                else:
                                    created_record[nested_field] = []

                # Add created records to merged data
                merged_data.extend(created_records_from_db)
                logger.info(f"Step 4: Added created records, total now {len(merged_data)} records")
            else:
                logger.info("Step 3: No newly created records found")

            # Step 4: Filter deleted records from merged state (if any deletions occurred)
            if deleted_ids_list:
                merged_data = filter_deleted_records_from_state(merged_data, deleted_ids_list, id_field)
                logger.info(f"Step 5: Filtered deleted records, {len(merged_data)} records remaining")

            # Step 5: Remove metadata fields before sending to Terraform
            metadata_fields = ["operation_type", "created_at", "updated_at",
                             "restored_by", "restored_at", "restored_from", "unique_id", "_id",
                             "deleted_by", "deleted_at", "deleted_from", "cascade_parent_id"]
            remove_metadata_fields(merged_data)

            # Also remove metadata from nested arrays
            for record in merged_data:
                for key, value in record.items():
                    if isinstance(value, list):
                        for item in value:
                            if isinstance(item, dict):
                                for field in metadata_fields:
                                    item.pop(field, None)

            logger.info(f"Step 6: Removed metadata fields from {len(merged_data)} records")
            logger.info(f"FINAL: Sending {len(merged_data)} complete records to Terraform")
            if deleted_ids_list:
                logger.info(f"DELETION: Requesting deletion of {len(deleted_ids_list)} IDs: {deleted_ids_list}")
            logger.info("=" * 80)

            modified_data = merged_data

            # Extract target parameters for Terraform API
            # If deletion occurred, add target_id and operation parameters
            params = extract_terraform_target_params(
                collection_name,
                modified_data,
                operation_type="delete" if deleted_records else None,
                target_ids=deleted_ids_list if deleted_records else None
            )

            # Get Okta authorization headers (Bearer token from session)
            tf_headers = get_okta_headers(request)

            # Get module-specific Terraform API endpoint
            from core.utils.module_mapping import get_terraform_api_for_entity

            terraform_api = get_terraform_api_for_entity(entity_name)

            if not terraform_api:
                logger.error(f"No Terraform API configured for entity: {entity_name}")
                return Response(
                    {"error": f"Entity '{entity_name}' not configured for Terraform deployment"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            # Build full Terraform URL with module-based endpoint
            terraform_url = f"{server_url}{terraform_api}"
            logger.info(f"Routing to Terraform module API: {terraform_url}")
            logger.info(f"Terraform params: {params}")

            # Send data to module-specific Terraform API
            # Pass all params including deletion parameters if applicable
            tf_response = requests.post(
                terraform_url,
                params=params,
                json={"data": modified_data},
                headers=tf_headers,
            )

            try:
                tf_data = tf_response.json()
            except Exception:
                tf_data = {"message": "Unknown response from TF repo"}

            tf_message = tf_data.get("message", "No message returned")

            # Handle deletion status update based on Terraform response
            if deleted_records:
                # Check if Terraform operation was successful (HTTP 2xx)
                if 200 <= tf_response.status_code < 300:
                    # SUCCESS: Update deletion status from "deletion_pending" to "deleted"
                    logger.info(f"Terraform deletion successful (status {tf_response.status_code}), updating deletion status")

                    # Update parent records
                    parent_ids = [doc.get(id_field) for doc in complete_deleted_records if doc.get(id_field)]
                    update_deletion_status(
                        current_db, entity_name, collection_name,
                        parent_ids, new_status="deleted"
                    )

                    # Update cascade deleted records (nested entities)
                    if cascade_info and "nested_deletions" in cascade_info:
                        for nested_field, nested_info in cascade_info["nested_deletions"].items():
                            nested_collection = nested_info["collection"]
                            nested_ids = nested_info["ids"]

                            # Update nested records to "deleted" status
                            update_deletion_status(
                                current_db, entity_name, nested_collection,
                                nested_ids, new_status="deleted"
                            )

                    logger.info(f"Successfully updated {len(deleted_ids_list)} records to 'deleted' status")

                else:
                    # FAILURE: Keep status as "deletion_pending" and return error
                    logger.error(f"Terraform deletion failed (status {tf_response.status_code}), keeping 'deletion_pending' status")

                    # Update all records to "deletion_failed" with error message
                    parent_ids = [doc.get(id_field) for doc in complete_deleted_records if doc.get(id_field)]
                    update_deletion_status(
                        current_db, entity_name, collection_name,
                        parent_ids, new_status="deletion_failed",
                        terraform_error=tf_message
                    )

                    # Update cascade deleted records as well
                    if cascade_info and "nested_deletions" in cascade_info:
                        for nested_field, nested_info in cascade_info["nested_deletions"].items():
                            nested_collection = nested_info["collection"]
                            nested_ids = nested_info["ids"]

                            update_deletion_status(
                                current_db, entity_name, nested_collection,
                                nested_ids, new_status="deletion_failed",
                                terraform_error=tf_message
                            )

                    # Return error response
                    return Response({
                        "error": "Terraform deletion failed",
                        "tf_message": tf_message,
                        "tf_status_code": tf_response.status_code,
                        "message": f"Deletion marked as failed. Records remain in 'deletion_failed' state in MongoDB for manual review.",
                        "failed_ids": deleted_ids_list,
                        "cascade_info": cascade_info
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Build response message based on operations performed
            operation_summary = []
            if deleted_records:
                operation_summary.append(f"{len(deleted_records)} deleted")
            if restore_records:
                operation_summary.append(f"{len(restore_records)} restored")
            if create_records:
                operation_summary.append(f"{len(create_records)} created")

            response_message = f"Operations completed: {', '.join(operation_summary)}" if operation_summary else "No operations performed"

            response_data = {
                "tf_message": tf_message,
                "message": response_message,
                "restored_db": current_db_name,
                "collection": f"_{collection_name}",
                "record_count": len(modified_data),
                "operations": {
                    "deleted": len(deleted_records),
                    "restored": len(restore_records),
                    "created": len(create_records),
                }
            }

            # Add cascade info if deletion occurred
            if deleted_records and cascade_info:
                response_data["cascade_info"] = cascade_info

            return Response(response_data, status=status.HTTP_201_CREATED)

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