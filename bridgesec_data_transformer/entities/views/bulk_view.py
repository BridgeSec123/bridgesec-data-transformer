import copy
import json
import logging
import os
import time
import traceback
import uuid
from datetime import datetime, timedelta

import requests
from core.authentication import CustomJWTAuthentication
from core.tasks.bulk_tasks import run_bulk_entity_task
from core.utils.progress_store import create_bulk_job
from core.utils.collection_mapping import (ENTITY_ID_MAPPING,
                                           NON_EDITABLE_FIELDS,
                                           RESOURCE_COLLECTION_MAP)
from core.utils.db_utils import (ENTITIES_WITH_BUILDERS, extract_time,
                                 get_collection_diff, get_collection_name,
                                 get_db_map, get_latest_db, list_databases_for_date,
                                 parse_input_date, resolve_db_name)
from core.utils.jwt_utils import get_user_from_request
from core.utils.model_registry import MODEL_REGISTRY
from core.utils.mongo_utils import ensure_mongo_connection, get_dynamic_db
from core.utils.nested_mapping import NESTED_FIELD_COLLECTIONS
from core.utils.okta_helpers import get_okta_headers
from core.utils.module_mapping import get_terraform_api_for_entity
from core.utils.restore_utils import (extract_terraform_target_params,
                                      fetch_and_merge_restored_data,
                                      remove_metadata_fields,
                                      store_restored_data_with_metadata,
                                      store_created_data,
                                      store_deleted_data_with_metadata,
                                      update_deletion_status,
                                      filter_deleted_records_from_state,
                                      handle_nested_deletion,
                                      validate_deletion_safety,
                                      update_created_records_with_ids,
                                      delete_latest_record,
                                      create_deletion_plan)
from core.utils.verification import verify_deletion_complete
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

from core.utils import fieldfetch
from core.utils import mapping_handlers
from bridgesec_logging import log_restore_operation, log_terraform_api_call, LogExecutionTime

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
        # Get request_id from middleware
        request_id = getattr(request, 'request_id', 'N/A')
        user = getattr(request.user, 'username', 'anonymous') if hasattr(request, 'user') else 'anonymous'

        logger.info(
            "Bulk fetch triggered",
            extra={
                'component': 'api',
                'request_id': request_id,
                'user': user,
            }
        )

        # Get Okta access token and granted scopes from session to pass to background task
        okta_access_token = None
        okta_granted_scopes = []
        if hasattr(request, 'session'):
            okta_access_token = request.session.get('okta_access_token')
            okta_granted_scopes = request.session.get('okta_granted_scopes', [])

        # Generate db_name here so the job doc and the Celery task use the same value.
        # create_bulk_job is called synchronously BEFORE .delay() so the job doc exists
        # in MongoDB by the time the frontend receives the response and subscribes to the
        # SSE stream — avoids "Job not found" race condition.
        db_name = get_dynamic_db()
        create_bulk_job(request_id, db_name, list(ENTITY_VIEWSETS.keys()))

        run_bulk_entity_task.delay(
            okta_access_token=okta_access_token,
            okta_granted_scopes=okta_granted_scopes,
            request_id=request_id,
            db_name=db_name,
        )

        logger.info(
            "Bulk fetch task queued successfully",
            extra={
                'component': 'celery',
                'request_id': request_id,
                'user': user,
            }
        )

        return Response(
            {"message": "Data fetch task triggered successfully", "request_id": request_id},
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

    @swagger_auto_schema(
        operation_description=(
            "Return snapshot database information.\n\n"
            "**No params** → date-level summary with snapshot counts only.\n"
            "**?date=DD-MM-YY** → paginated snapshots for that date (use page + page_size).\n"
            "**?date=DD-MM-YY&time=HH:MM** → confirm a specific snapshot exists."
        ),
        manual_parameters=[
            openapi.Parameter(
                "date", openapi.IN_QUERY,
                description="Filter by date. Format: DD-MM-YY or DD-MM-YYYY (e.g. 10-03-26)",
                type=openapi.TYPE_STRING, required=False,
            ),
            openapi.Parameter(
                "time", openapi.IN_QUERY,
                description="Confirm a specific snapshot (requires date). Format: HH:MM (e.g. 03:57)",
                type=openapi.TYPE_STRING, required=False,
            ),
            openapi.Parameter(
                "page", openapi.IN_QUERY,
                description="Page number for paginated snapshot list (requires date). Default: 1",
                type=openapi.TYPE_INTEGER, required=False,
            ),
            openapi.Parameter(
                "page_size", openapi.IN_QUERY,
                description="Number of snapshots per page (requires date). Default: 20",
                type=openapi.TYPE_INTEGER, required=False,
            ),
        ],
        responses={
            200: openapi.Response("Snapshot data"),
            400: "Invalid date, time, or pagination format",
            404: "No snapshots found",
        },
    )
    @action(detail=False, methods=["get"], url_path="db-map")
    def get_db_map_view(self, request):
        """
        GET /db-map/
            → date summary: {"10-03-2026": {"snapshot_count": 3}, ...}

        GET /db-map/?date=10-03-26&page=1&page_size=20
            → paginated snapshots for that date

        GET /db-map/?date=10-03-26&time=03:57
            → confirm a specific snapshot exists
        """
        date_param = request.query_params.get("date")
        time_param = request.query_params.get("time")

        try:
            # ?date + ?time — confirm specific snapshot exists
            if date_param and time_param:
                parsed = parse_input_date(date_param)
                if parsed is None:
                    return Response(
                        {"error": "Invalid date format. Use DD-MM-YY or DD-MM-YYYY"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                iso_date = parsed.strftime("%Y-%m-%d")
                db_name = resolve_db_name(iso_date, time_param)
                if db_name not in mongo_client.list_database_names():
                    return Response(
                        {"error": f"No snapshot found for {date_param} at {time_param}"},
                        status=status.HTTP_404_NOT_FOUND,
                    )
                display_date = f"{iso_date[8:]}-{iso_date[5:7]}-{iso_date[:4]}"
                return Response(
                    {
                        "dates": [
                            {
                                "date": display_date,
                                "snapshot_count": 1,
                                "snapshots": [{"time": time_param, "db_name": db_name}],
                            }
                        ]
                    },
                    status=status.HTTP_200_OK,
                )

            # ?date only — paginated snapshots for that date
            if date_param:
                try:
                    page = int(request.query_params.get("page", 1))
                    page_size = int(request.query_params.get("page_size", 20))
                except ValueError:
                    return Response(
                        {"error": "page and page_size must be integers"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                if page < 1 or page_size < 1:
                    return Response(
                        {"error": "page and page_size must be positive integers"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                result = list_databases_for_date(mongo_client, date_param, page=page, page_size=page_size)
                if not result.get("dates") or result["dates"][0]["snapshot_count"] == 0:
                    return Response(
                        {"error": f"No snapshots found for {date_param}"},
                        status=status.HTTP_404_NOT_FOUND,
                    )
                return Response(result, status=status.HTTP_200_OK)

            # No params — date summary only (no snapshot details)
            result = get_db_map(mongo_client)
            if not result.get("dates"):
                return Response({"error": "No snapshots found"}, status=status.HTTP_404_NOT_FOUND)
            return Response(result, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"get_db_map_view failed: {e}")
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

    @action(detail=False, methods=["get"], url_path="resources")
    def get_resource_names(self, request):
        """
        Return available entity types or sub-entities.
        """
        logger.info("Returning available entity types or sub-entities....",extra={"operation":"FETCH-ENTITIES"})
        try:
            entity_type = request.query_params.get("entity_type")

            if entity_type:
                logger.info("Entities found",extra={"operation":"FETCH-ENTITIES"})
                entity_type = entity_type.title()
                sub_entities = RESOURCE_COLLECTION_MAP.get(entity_type)
                if not sub_entities:
                    logger.info("Sub entities not found",extra={"operation":"FETCH-ENTITIES"})
                    return Response(
                        {"detail": f"No sub-entities found for '{entity_type}'"},
                        status=status.HTTP_404_NOT_FOUND,
                    )
                display_names = [value for entry in sub_entities for value in entry.keys()]
                return Response({"data": display_names}, status=status.HTTP_200_OK)

            logger.info("Entities Not found",extra={"operation":"FETCH-ENTITIES"})
            return Response(
                {"data": sorted(RESOURCE_COLLECTION_MAP.keys())},
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @swagger_auto_schema(
        operation_description=(
            "Fetch paginated resource data from a specific snapshot DB.\n\n"
            "**`db_name` only** → paginate through all entities: `page` selects the entity "
            "(total_pages = entity count), `page_size` paginates records within that entity.\n\n"
            "**`db_name` + `entity_name`** → paginate records for that single entity "
            "(`page` / `page_size` / `total_pages` all refer to records)."
        ),
        manual_parameters=[
            openapi.Parameter(
                "db_name", openapi.IN_QUERY,
                description="Snapshot DB name (e.g. bridgesec_2026-03-10T0357)",
                type=openapi.TYPE_STRING, required=True,
            ),
            openapi.Parameter(
                "entity_name", openapi.IN_QUERY,
                description="Entity name (e.g. 'Okta Apps'). Omit to iterate over all entities.",
                type=openapi.TYPE_STRING, required=False,
            ),
            openapi.Parameter(
                "page", openapi.IN_QUERY,
                description=(
                    "Without entity_name: entity index (1 = first entity). "
                    "With entity_name: record page number. Default: 1"
                ),
                type=openapi.TYPE_INTEGER, required=False,
            ),
            openapi.Parameter(
                "page_size", openapi.IN_QUERY,
                description="Records per page within the selected entity. Default: 20",
                type=openapi.TYPE_INTEGER, required=False,
            ),
            openapi.Parameter(
                "data_page", openapi.IN_QUERY,
                description="Record page within the current entity (only used when entity_name is omitted). Default: 1",
                type=openapi.TYPE_INTEGER, required=False,
            ),
        ],
        responses={
            200: openapi.Response("Paginated resource data"),
            400: "Invalid or missing parameters",
            404: "Snapshot or entity not found",
        },
    )
    @action(detail=False, methods=["get"], url_path="data")
    def get_resource_data(self, request):
        """
        GET /data/?db_name=<db_name>[&entity_name=<entity_name>][&page=1][&page_size=20]

        Without entity_name: page iterates entities; page_size paginates that entity's records.
        With entity_name: page/page_size paginate that entity's records directly.
        """
        db_name = request.query_params.get("db_name")
        entity_name = request.query_params.get("entity_name")

        if not db_name:
            return Response(
                {"error": "Missing required query parameter: 'db_name'"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            page = int(request.query_params.get("page", 1))
            page_size = int(request.query_params.get("page_size", 20))
        except ValueError:
            return Response(
                {"error": "page and page_size must be integers"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if page < 1 or page_size < 1:
            return Response(
                {"error": "page and page_size must be positive integers"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            if db_name not in mongo_client.list_database_names():
                return Response(
                    {"error": f"Snapshot '{db_name}' not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            iso_date = db_name.split("_", 1)[1].split("T")[0]
            service = EntityDataService()

            # ── ALL-ENTITIES MODE (no entity_name) ──────────────────────────
            if not entity_name:
                logger.info("All-entities paginated fetch", extra={"operation": "FETCH-ALL-ENTITIES"})

                all_entity_names = [
                    display_name
                    for entries in RESOURCE_COLLECTION_MAP.values()
                    for entry in entries
                    for display_name in entry.keys()
                    if display_name != "non_editable_field"
                ]
                total_entities = len(all_entity_names)

                if page > total_entities:
                    return Response(
                        {"error": f"page must be between 1 and {total_entities}"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                current_entity = all_entity_names[page - 1]
                logger.info(f"Entity page {page}/{total_entities} → {current_entity}", extra={"operation": "FETCH-ALL-ENTITIES"})

                original_data = service.fetch(iso_date, current_entity, db_name=db_name)

                collection_name = get_collection_name(current_entity)
                id_field = ENTITY_ID_MAPPING.get(current_entity)
                if collection_name and id_field:
                    db = mongo_client[db_name]
                    original_data = fetch_and_merge_restored_data(
                        db, current_entity, collection_name, id_field, original_data
                    )

                original_data = [
                    record for record in original_data
                    if record.get("operation_type") not in ["deleted", "deletion_pending", "deletion_failed"]
                ]

                remove_metadata_fields(original_data)

                total_records = len(original_data)
                data_total_pages = max(1, (total_records + page_size - 1) // page_size)
                data_page = int(request.query_params.get("data_page", 1))
                if data_page < 1:
                    data_page = 1
                start = (data_page - 1) * page_size
                end = start + page_size

                logger.info(
                    f"Returning records {start + 1}–{min(end, total_records)} of {total_records} for {current_entity}",
                    extra={"operation": "FETCH-ALL-ENTITIES"},
                )

                return Response(
                    {
                        "page": page,
                        "total_pages": total_entities,
                        "next_page": page + 1 if page < total_entities else None,
                        "prev_page": page - 1 if page > 1 else None,
                        "entity": current_entity,
                        "data_page": data_page,
                        "page_size": page_size,
                        "data_total_pages": data_total_pages,
                        "total_records": total_records,
                        "next_data_page": data_page + 1 if data_page < data_total_pages else None,
                        "prev_data_page": data_page - 1 if data_page > 1 else None,
                        "non_editable_fields": NON_EDITABLE_FIELDS.get(current_entity, []),
                        "data": original_data[start:end],
                    },
                    status=status.HTTP_200_OK,
                )

            # ── SINGLE-ENTITY MODE ───────────────────────────────────────────
            entity_name = " ".join(entity_name.split())
            logger.info(f"Single-entity fetch: {entity_name}", extra={"operation": "FETCH-CURRENT-DATA"})

            original_data = service.fetch(iso_date, entity_name, db_name=db_name)
            logger.info(f"Fetched {len(original_data)} records for {entity_name}", extra={"operation": "FETCH-CURRENT-DATA"})

            collection_name = get_collection_name(entity_name)
            id_field = ENTITY_ID_MAPPING.get(entity_name)
            if collection_name and id_field:
                db = mongo_client[db_name]
                original_data = fetch_and_merge_restored_data(
                    db, entity_name, collection_name, id_field, original_data
                )
                logger.info(f"Merge complete: {len(original_data)} records", extra={"operation": "FETCH-CURRENT-DATA"})

            original_data = [
                record for record in original_data
                if record.get("operation_type") not in ["deleted", "deletion_pending", "deletion_failed"]
            ]

            remove_metadata_fields(original_data)

            total_records = len(original_data)
            total_pages = max(1, (total_records + page_size - 1) // page_size)

            if page > total_pages:
                return Response(
                    {"error": f"page must be between 1 and {total_pages}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            start = (page - 1) * page_size
            end = start + page_size

            logger.info(
                f"Returning records {start + 1}–{min(end, total_records)} of {total_records}",
                extra={"operation": "FETCH-CURRENT-DATA"},
            )

            return Response(
                {
                    "entity": entity_name,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": total_pages,
                    "total_records": total_records,
                    "next_page": page + 1 if page < total_pages else None,
                    "prev_page": page - 1 if page > 1 else None,
                    "non_editable_fields": NON_EDITABLE_FIELDS.get(entity_name, []),
                    "data": original_data[start:end],
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(f"Error in get_resource_data: {str(e)}", exc_info=True, extra={"operation": "FETCH-CURRENT-DATA"})
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
            ),
            openapi.Parameter(
                name="source_db",
                in_=openapi.IN_QUERY,
                description="Source snapshot DB to restore data from (e.g. bridgesec_2026-03-28T0000). Applies to restore operations only — sets 'restored_from' metadata and drives the Terraform merge source. Defaults to db_name in the URL.",
                type=openapi.TYPE_STRING,
                required=False,
            ),
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
        url_path=r"restore/(?P<db_name>[^/]+)/(?P<entity_name>[^/.]+)",
    )
    def restore_modified_data(self, request, db_name, entity_name):
        """
        Restore data into the specified snapshot DB using pymongo only.

        Query Parameters:
            - operation_type: "delete", "restore", or "create" (optional)
                If "delete", all records in body are treated as deletion targets
        """
        # Get request_id and user for tracing
        request_id = getattr(request, 'request_id', 'N/A')
        user = get_user_from_request(request)
        restored_by = get_user_from_request(request)

        try:
            # Validate snapshot DB exists
            if db_name not in mongo_client.list_database_names():
                return Response(
                    {"error": f"Snapshot '{db_name}' not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Get operation_type from query parameters
            operation_type = request.query_params.get("operation_type")

            # "plan" — return terraform plan output to user without executing apply.
            # Omit (or any other value) to execute immediately (existing behaviour).
            phase = request.query_params.get("phase")

            # Optional: source snapshot DB to restore from. Applies to restore operations only.
            # If provided, restored_from metadata and Terraform merge source use this DB instead of db_name.
            srcdb = request.query_params.get("source_db")
            if srcdb and srcdb not in mongo_client.list_database_names():
                return Response(
                    {"error": f"Source DB '{srcdb}' not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            source_db = srcdb if srcdb else db_name

            # Extract iso_date from source_db: "bridgesec_2026-03-10T0357" → "2026-03-10"
            iso_date = source_db.split("_", 1)[1].split("T")[0]

            modified_data = request.data.get("data", [])
            if not isinstance(modified_data, list):
                return Response(
                    {"error": "Invalid data format. 'data' must be a list"},
                    status=400,
                )

            logger.info(
                f"Restore operation started: {entity_name}",
                extra={
                    'component': 'restore',
                    'request_id': request_id,
                    'user': user,
                    'entity_type': entity_name,
                    'operation': "Restore Modified Data",
                    'record_count': len(modified_data),
                    'source_date': iso_date,
                }
            )

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

            logger.info(f"Using snapshot db: {db_name}", extra={"operation": "Restore Modified Data"})

            # Both source and write target are the same exact snapshot db
            current_db = mongo_client[db_name]

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
                logger.info(f"Delete operation: {len(deleted_records)} records marked for deletion",extra={"operation":"Restore Modified Data"})

            else:
                # Auto-detect operation based on presence of ID field
                for doc in modified_data:
                    has_id = doc.get(id_field) is not None

                    if has_id:
                        restore_records.append(doc)
                    else:
                        create_records.append(doc)
                logger.info(f"Auto-detected: {len(restore_records)} restored, {len(create_records)} created",extra={"operation":"Restore Modified Data"})

            logger.info(f"Operation counts: {len(deleted_records)} deleted, {len(restore_records)} restored, {len(create_records)} created",extra={"operation":"Restore Modified Data"})

            # Initialize variables for deletion tracking
            deleted_ids_list = []
            cascade_info = {}

            # Process deletion operations
            if deleted_records:
                logger.info(f"Processing {len(deleted_records)} deletion(s)")

                # Validate deletion safety
                errors = validate_deletion_safety(current_db, entity_name, collection_name, deleted_records)
                if errors:
                    return Response(
                        {"error": "Deletion validation failed", "details": errors},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # Generate plan_id early so it can be tagged on every stored record.
                # This links _<collection_name> records to the plan in pending_deletion_plans.
                plan_id = uuid.uuid4().hex

                # Fetch complete records from source DB for each deleted record
                complete_deleted_records = []
                for doc in deleted_records:
                    if not mapping_handlers.is_mapped_entity(collection_name):
                        complete_record = fieldfetch.get_collection(current_db, collection_name, doc)
                    else:
                        complete_record = fieldfetch.get_mapped_collection(current_db, collection_name, doc)

                    if complete_record:
                        complete_deleted_records.append(complete_record)

                logger.info(f"Fetched {len(complete_deleted_records)} complete records for deletion",extra={"operation":"Restore Modified Data"})

                # Store deleted records in _<collection_name> tagged with plan_id.
                # These ARE the plan data — pending_deletion_plans only stores metadata.
                store_deleted_data_with_metadata(
                    current_db, entity_name, collection_name,
                    complete_deleted_records, restored_by, db_name,
                    operation_type="deletion_pending",
                    plan_id=plan_id,
                )

                # Handle cascade deletion for nested entities (also tagged with plan_id)
                deleted_ids_list, cascade_info = handle_nested_deletion(
                    current_db, entity_name, complete_deleted_records,
                    restored_by, db_name, plan_id=plan_id,
                )

                logger.info(f"Cascade deletion complete: {len(deleted_ids_list)} total IDs marked as deletion_pending",extra={"operation":"Restore Modified Data"})

            # Process restore operations
            if restore_records:
                logger.info(f"Processing {len(restore_records)} restore(s)", extra={"operation":"Restore Modified Data"})
                if not mapping_handlers.is_mapped_entity(collection_name):
                    for i, doc in enumerate(restore_records):
                        new_data = fieldfetch.get_collection(current_db, collection_name, doc)
                        restore_records[i] = new_data
                else:
                    for i, doc in enumerate(restore_records):
                        data = fieldfetch.get_mapped_collection(current_db, collection_name, doc)
                        restore_records[i] = data

            # Process create operations
            if create_records:
                logger.info(f"Processing {len(create_records)} creation(s)",extra={"operation":"Restore Modified Data"})
                for i, doc in enumerate(create_records):
                    create_records[i] = fieldfetch.transform_data(collection_name, doc)

            # Store restored and created data (deleted data was already stored above)
            if restore_records:
                data_for_storage = copy.deepcopy(restore_records)
                store_restored_data_with_metadata(
                    current_db, entity_name, collection_name,
                    data_for_storage, restored_by, source_db
                )
                logger.info(f"Stored {len(restore_records)} restored records",extra={"operation":"Restore Modified Data"})

            if create_records:
                data_for_storage = copy.deepcopy(create_records)
                store_created_data(
                    current_db, entity_name, collection_name,
                    data_for_storage,
                )
                logger.info(f"Stored {len(create_records)} created records",extra={"operation":"Restore Modified Data"})

            # CRITICAL: Fetch ALL records from source DB and merge with restored/created data
            # This ensures Terraform receives complete state (not just modified records)
            # to prevent unintended resource deletion

            logger.info("=" * 80)
            logger.info("MERGING COLLECTIONS FOR TERRAFORM",extra={"operation":"Restore Modified Data"})
            logger.info("=" * 80)

            # Step 1: Fetch ALL original data from source DB snapshot
            service = EntityDataService()
            original_data = service.fetch(iso_date, entity_name, db_name=source_db)
            logger.info(f"Step 1: Fetched {len(original_data)} original records from source DB ({source_db})",extra={"operation":"Restore Modified Data"})

            # Step 2: Merge original data with restored data from today's DB
            # This handles both simple entities and nested entities (with builders)
            restored_collection = current_db[f"_{collection_name}"]
            created_records_from_db = list(restored_collection.find(
                {"operation_type": "created"},
                {"_id": 0}
            ))
            # Note: fetch_and_merge_restored_data now filters out deleted records automatically
            merged_data = fetch_and_merge_restored_data(
                current_db, entity_name, collection_name, id_field, original_data
            )
            logger.info(f"Step 2: Merged to {len(merged_data)} total records (original + restored, deleted filtered)",extra={"operation":"Restore Modified Data"})

            # Step 3: Add newly created records that are NOT already in merged_data.
            # Created records with a real ID (written back after Terraform apply) are already
            # included by merge_restored_with_original() Pass 2. Only add records that are
            # still missing from merged_data (e.g. ID not yet written back, or nested entities
            # that need unique_id-based assembly).
            restored_collection = current_db[f"_{collection_name}"]
            created_records_from_db = list(restored_collection.find(
                {"operation_type": "created"},
                {"_id": 0}
            ))

            if created_records_from_db:
                logger.info(f"Step 3: Found {len(created_records_from_db)} newly created records",extra={"operation":"Restore Modified Data"})

                # Build set of IDs already present in merged_data to avoid duplicates
                merged_ids = {str(r.get(id_field)) for r in merged_data if r.get(id_field)}

                # For created records with nested data, rebuild nested arrays
                nested_mapping = NESTED_FIELD_COLLECTIONS.get(entity_name)
                records_to_add = []
                for created_record in created_records_from_db:
                    rec_id = created_record.get(id_field)
                    # Skip if already present in merged_data (added by merge_restored_with_original Pass 2)
                    if rec_id and str(rec_id) in merged_ids:
                        logger.info(f"Step 3: Skipping created record id={rec_id} — already in merged_data",extra={"operation":"Restore Modified Data"})
                        continue

                    if nested_mapping:
                        unique_id = created_record.get("unique_id")
                        if unique_id:
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

                    records_to_add.append(created_record)

                merged_data.extend(records_to_add)
                logger.info(f"Step 4: Added {len(records_to_add)} new created record(s), total now {len(merged_data)} records",extra={"operation":"Restore Modified Data"})
            else:
                logger.info("Step 3: No newly created records found",extra={"operation":"RestoreModifiedData"})

            # Step 4: Filter deleted records from merged state
            if deleted_ids_list:
                merged_data = filter_deleted_records_from_state(merged_data, deleted_ids_list, id_field)
                logger.info(f"Step 5: Filtered deleted records, {len(merged_data)} records remaining",extra={"operation":"Restore Modified Data"})

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

            logger.info(f"Step 6: Removed metadata fields from {len(merged_data)} records",extra={"operation":"Restore Modified Data"})
            logger.info(f"FINAL: Sending {len(merged_data)} complete records to Terraform",extra={"operation":"Restore Modified Data"})
            if deleted_ids_list:
                logger.info(f"DELETION: Requesting deletion of {len(deleted_ids_list)} IDs: {deleted_ids_list}",extra={"operation":"Restore Modified Data"})
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
            terraform_api = get_terraform_api_for_entity(entity_name)

            if not terraform_api:
                logger.error(f"No Terraform API configured for entity: {entity_name}",extra={"operation":"Restore Modified Data"})
                return Response(
                    {"error": f"Entity '{entity_name}' not configured for Terraform deployment"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            # Build full Terraform URL with module-based endpoint
            terraform_url = f"{server_url}{terraform_api}"

            # ------------------------------------------------------------------
            # PLAN GATE: all deletes go through plan/confirm flow.
            # BDT adds phase=plan internally on the OkTf call — the client
            # only needs to pass operation_type=delete.
            # ------------------------------------------------------------------
            if deleted_records:
                plan_params = {**params, "phase": "plan"}
                logger.info(
                    f"Phase=plan: calling OkTf for plan output (no apply)",
                    extra={"operation": "Restore Modified Data", "entity": entity_name}
                )
                tf_plan_response = requests.post(
                    terraform_url,
                    params=plan_params,
                    json={"data": modified_data},
                    headers=get_okta_headers(request),
                )
                if not tf_plan_response.ok:
                    try:
                        err_detail = tf_plan_response.json()
                    except Exception:
                        err_detail = {"raw": tf_plan_response.text}
                    return Response(
                        {"error": "Terraform plan failed", "details": err_detail},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )

                plan_output = tf_plan_response.json()
                deletion_summary = plan_output.pop("deletion_summary", None)

                # Store plan metadata in pending_deletion_plans.
                # Records are already in _<collection_name> tagged with plan_id —
                # no duplication here.
                plans_col = mongo_client[settings.MONGO_DB_NAME]["pending_deletion_plans"]
                create_deletion_plan(
                    plan_id=plan_id,
                    db_name=db_name,
                    entity_name=entity_name,
                    collection_name=collection_name,
                    id_field=id_field,
                    merged_data=modified_data,
                    terraform_params=params,   # params WITHOUT phase=plan for Phase 2
                    terraform_url=terraform_url,
                    plan_output=plan_output,
                    cascade_info=cascade_info,
                    created_by=restored_by,
                    plans_collection=plans_col,
                )

                response_data = {
                    "phase": "plan",
                    "plan_id": plan_id,
                    "expires_at": (datetime.utcnow() + timedelta(minutes=15)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "plan_output": plan_output,
                    "message": (
                        "Review the plan and confirm deletion via "
                        f"POST /confirm-delete/{plan_id}/ within 15 minutes."
                    ),
                }
                if deletion_summary is not None:
                    response_data["deletion_summary"] = deletion_summary

                return Response(response_data, status=status.HTTP_200_OK)
            # ------------------------------------------------------------------
            # END PLAN GATE
            # ------------------------------------------------------------------

            logger.info(
                f"Sending to Terraform API: {terraform_url}",
                extra={
                    'component': 'terraform_api',
                    'request_id': request_id,
                    'entity_type': entity_name,
                    'terraform_url': terraform_url,
                    'params': params,
                    "operation":"Restore Modified Data",
                }
            )

            # Send data to module-specific Terraform API with timing
            start_time = time.time()

            tf_response = requests.post(
                terraform_url,
                params=params,
                json={"data": modified_data},
                headers=tf_headers,
            )
            if not tf_response.ok:
                delete_latest_record(entity_name,mongo_client,iso_date)

            duration_ms = int((time.time() - start_time) * 1000)

            try:
                tf_data = tf_response.json()
            except Exception:
                tf_data = {"message": "Unknown response from TF repo"}

            tf_message = tf_data.get("message", "No message returned")

            # Log Terraform API response
            log_terraform_api_call(
                entity_type=entity_name,
                operation=operation_type or 'restore',
                status_code=tf_response.status_code,
                duration_ms=duration_ms,
                request_id=request_id
            )

            logger.info(
                f"Terraform API response: {tf_response.status_code}",
                extra={
                    'component': 'terraform_api',
                    'request_id': request_id,
                    'entity_type': entity_name,
                    'status_code': tf_response.status_code,
                    'duration_ms': duration_ms,
                    'response_message': tf_message,  # Renamed from 'message' (reserved field)
                    "operation":"Restore Modified Data",
                }
            )

            # Handle deletion status update based on Terraform response
            if deleted_records:
                # Check if Terraform operation was successful (HTTP 2xx)
                if 200 <= tf_response.status_code < 300:
                    # SUCCESS: Update deletion status from "deletion_pending" to "deleted"
                    logger.info(f"Terraform deletion successful (status {tf_response.status_code}), updating deletion status",extra={"operation":"Restore Modified Data"})

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

                    logger.info(f"Successfully updated {len(deleted_ids_list)} records to 'deleted' status",extra={"operation":"Restore Modified Data"})

                    # ============================================
                    # NEW: RUN DELETION VERIFICATION
                    # ============================================
                    logger.info("=" * 80)
                    logger.info("RUNNING DELETION VERIFICATION",extra={"operation":"Restore Modified Data"})
                    logger.info("=" * 80)

                    # Get Okta access token from request session
                    okta_access_token = None
                    if hasattr(request, 'session'):
                        okta_access_token = request.session.get('okta_access_token')

                    # Run verification for each deleted record
                    verification_results = []
                    for doc in complete_deleted_records:
                        try:
                            verification = verify_deletion_complete(
                                entity_type=entity_name,
                                entity_record=doc,
                                deletion_results=tf_data,
                                access_token=okta_access_token
                            )
                            verification_results.append(verification)
                        except Exception as e:
                            logger.error(f"Verification failed for record: {e}")
                            verification_results.append({
                                "verified": False,
                                "error": str(e),
                                "entity_record": doc
                            })

                    # Log verification summary
                    verified_count = sum(1 for v in verification_results if v.get("verified"))
                    failed_count = len(verification_results) - verified_count

                    logger.info(f"VERIFICATION SUMMARY: {verified_count} verified, {failed_count} failed",extra={"operation":"Restore Modified Data"})
                    logger.info("=" * 80)

                else:
                    # FAILURE: Keep status as "deletion_pending" and return error
                    logger.error(f"Terraform deletion failed (status {tf_response.status_code}), keeping 'deletion_pending' status",extra={"operation":"Restore Modified Data"})

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

            # If Terraform succeeded and we created new records, update MongoDB with real Okta IDs.
            # Terraform state now contains the actual IDs assigned by Okta for newly created resources.
            # We match records by their label/name field (entity_unique_fields) and write the real ID.
            if create_records and 200 <= tf_response.status_code < 300:
                created_resources = tf_data.get("created_resources", [])
                if created_resources:
                    label_field = mapping_handlers.MAPPED_ENTITIES_HELPERS["entity_unique_fields"].get(
                        collection_name, "label"
                    )
                    label_to_id_map = {r["label"]: r["id"] for r in created_resources}
                    update_created_records_with_ids(
                        current_db, collection_name, id_field, label_field, label_to_id_map
                    )
                    logger.info(
                        f"Updated {len(label_to_id_map)} created record(s) with real IDs from Terraform state",
                        extra={"operation": "Restore Modified Data"},
                    )

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
                "restored_db": db_name,
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

            # Add verification results if deletion occurred
            if deleted_records and 'verification_results' in locals():
                response_data["verification"] = {
                    "performed": True,
                    "total_verified": sum(1 for v in verification_results if v.get("verified")),
                    "total_failed": sum(1 for v in verification_results if not v.get("verified")),
                    "results": verification_results
                }

                # Update status based on verification
                if any(not v.get("verified") for v in verification_results):
                    response_data["warning"] = "Deletion completed but verification found issues. Check 'verification' field for details."

            # Log operation completion
            log_restore_operation(
                entity_type=entity_name,
                operation_type=operation_type or 'restore',
                count=len(modified_data),
                request_id=request_id,
                user=user
            )

            logger.info(
                f"Restore operation completed: {entity_name}",
                extra={
                    'component': 'restore',
                    'request_id': request_id,
                    'user': user,
                    'entity_type': entity_name,
                    'deleted_count': len(deleted_records),
                    'restored_count': len(restore_records),
                    'created_count': len(create_records),  # Renamed from 'created' (reserved field)
                    'terraform_status': tf_response.status_code,
                    "operation":"Restore Modified Data",
                }
            )

            return Response(response_data, status=status.HTTP_201_CREATED)

        except Exception as e:
            traceback.print_exc()

            logger.error(
                f"Restore operation failed: {entity_name} - {str(e)}",
                extra={
                    'component': 'restore',
                    'request_id': request_id,
                    'user': user,
                    'entity_type': entity_name,
                    'error': str(e),
                    "operation":"Restore Modified Data",
                },
                exc_info=True
            )

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
            traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                "base_db",
                openapi.IN_QUERY,
                description="Base snapshot DB name (e.g. bridgesec_2026-03-10T0357)",
                type=openapi.TYPE_STRING,
                required=True,
            ),
            openapi.Parameter(
                "target_db",
                openapi.IN_QUERY,
                description="Target snapshot DB name to compare against base",
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
        Compare two collection snapshots by DB name.
        """
        try:
            # Get query parameters
            base_db = request.query_params.get("base_db")
            target_db = request.query_params.get("target_db")

            # Validation
            if not entity_name:
                return Response(
                    {"error": "Path parameter 'entity_name' is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not base_db or not target_db:
                return Response(
                    {"error": "Query parameters 'base_db' and 'target_db' are required"},
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

            # Validate DB snapshots exist
            mongo_client = settings.MONGO_CLIENT
            for db_param, label in [(base_db, "base_db"), (target_db, "target_db")]:
                if db_param not in mongo_client.list_database_names():
                    return Response(
                        {"error": f"Snapshot '{db_param}' not found", "param": label},
                        status=status.HTTP_404_NOT_FOUND
                    )

            # Get ID field for this entity
            id_field = ENTITY_ID_MAPPING[entity_name]

            # Extract iso dates from db names for service calls
            base_date = base_db.split("_", 1)[1].split("T")[0]
            target_date = target_db.split("_", 1)[1].split("T")[0]

            # Use EntityDataService to get rebuilt data with nested arrays
            service = EntityDataService()
            old_docs = service.fetch(base_date, entity_name, db_name=base_db)
            new_docs = service.fetch(target_date, entity_name, db_name=target_db)

            # Merge any restored/reverted records from _<collection> into both sides
            # so that reverted fields are reflected before diffing.
            # Also strip internal metadata fields (operation_type, restored_by, etc.)
            # to prevent them from surfacing as false field-level changes.
            collection_name = get_collection_name(entity_name)
            if collection_name:
                old_docs = fetch_and_merge_restored_data(
                    mongo_client[base_db], entity_name, collection_name, id_field, old_docs
                )
                new_docs = fetch_and_merge_restored_data(
                    mongo_client[target_db], entity_name, collection_name, id_field, new_docs
                )
                remove_metadata_fields(old_docs)
                remove_metadata_fields(new_docs)

            if not old_docs and not new_docs:
                return Response(
                    {
                        "error": f"No data found for entity '{entity_name}' in either snapshot",
                        "base_db": base_db,
                        "target_db": target_db
                    },
                    status=status.HTTP_404_NOT_FOUND
                )

            # Get structured diff with nested array comparison for entities with builders
            diff_result = get_collection_diff(
                old_docs,
                new_docs,
                id_field,
                entity_name=entity_name,
                base_db=base_db,
                target_db=target_db
            )

            # Add non-editable fields configuration to response
            non_editable_fields = NON_EDITABLE_FIELDS.get(entity_name, [])
            diff_result["non_editable_fields"] = non_editable_fields

            return Response(diff_result, status=status.HTTP_200_OK)

        except Exception as e:
            traceback.print_exc()
            logger.error(f"Error in diff_collections: {str(e)}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
