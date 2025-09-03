import json
import os
import re
from datetime import datetime

from entities.serializers.restore_serializer import RestoreDataSerializer
from core.utils.collection_mapping import RESOURCE_COLLECTION_MAP
from core.utils.mongo_utils import get_dynamic_db, ensure_mongo_connection
from django.conf import settings
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from pymongo import MongoClient
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from core.tasks.bulk_tasks import run_bulk_entity_task

from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from core.authentication import CustomJWTAuthentication
from entities.registry import ENTITY_VIEWSETS
import requests

mongo_client = settings.MONGO_CLIENT 
server_url = settings.SERVER_URL


def extract_time(db_name):
    """Extract HH:MM from db name like bridgesec_2025-08-28T0930."""
    try:
        time_part = db_name.split("T")[1]
        return f"{time_part[:2]}:{time_part[2:]}"
    except Exception:
        return None

def get_collection_name(entity_name):
    """Resolve collection name from entity name using RESOURCE_COLLECTION_MAP."""
    for group in RESOURCE_COLLECTION_MAP.values():
        for mapping in group:
            if entity_name in mapping:
                return mapping[entity_name]
    return None


def get_latest_db(mongo_client, date_str):
    """
    Utility: Return the latest DB name for a given date.
    Works for any feature needing latest DB resolution.
    """
    all_dbs = mongo_client.list_database_names()
    date_prefix = f"{settings.MONGO_DB_NAME}_{date_str}"
    matching_dbs = [db for db in all_dbs if db.startswith(date_prefix)]
    if not matching_dbs:
        return None
    return sorted(matching_dbs)[-1]


class BulkEntityViewSet(viewsets.ViewSet):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = RestoreDataSerializer

    @swagger_auto_schema(
        operation_description="Fetch data from all registered entity APIs and store them in MongoDB",
        responses={201: openapi.Response("Data fetched and stored successfully")},
    )
    def post(self, request):
        """
        Fetch fresh data for all registered entities and store them in a dynamic MongoDB.
        This flow uses mongoengine models → keep ensure_mongo_connection.
        """
        db_name = get_dynamic_db()
        ensure_mongo_connection(db_name)  # needed since models use mongoengine

        for entity_name, viewset_class in ENTITY_VIEWSETS.items():
            viewset_instance = viewset_class()
            extracted_data = viewset_instance.fetch_and_store_data(db_name)
            if not extracted_data:
                return Response(
                    {"error": f"Failed to fetch {entity_name} data"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            # Save extracted data to local JSON
            output_dir = os.path.join(settings.BASE_DIR, "output", db_name)
            os.makedirs(output_dir, exist_ok=True)

            for sub_entity_name, sub_entity_data in extracted_data.items():
                file_name = f"{sub_entity_name}.json"
                file_path = os.path.join(output_dir, file_name)
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(sub_entity_data, f, ensure_ascii=False, indent=4)

        return Response(
            {"message": "Data fetched and stored successfully", "db_name": db_name},
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
        Fetch data from Mongo using pymongo → no ensure_mongo_connection needed.
        """
        if not date_str or not entity_name:
            return Response(
                {"error": "Missing 'date' or 'entity_type' parameter"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            latest_db = get_latest_db(mongo_client, date_str)
            if not latest_db:
                return Response(
                    {
                        "message": f"No matching databases found for the given date: {date_str}",
                        "data": [],
                    },
                    status=status.HTTP_200_OK,
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

            db = mongo_client[latest_db]
            data = list(db[collection_name].find({}, {"_id": 0}))
            return Response(data, status=status.HTTP_200_OK)

        except Exception as e:
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

            source_db = mongo_client[source_db_name]
            new_db_name = get_dynamic_db()
            new_db = mongo_client[new_db_name]

            for coll in source_db.list_collection_names():
                source_collection = source_db[coll]
                target_collection = new_db[coll]

                if coll == collection_name:
                    for doc in modified_data:
                        doc.pop("_id", None)
                    if modified_data:
                        target_collection.insert_many(modified_data)
                else:
                    docs = list(source_collection.find({}))
                    for doc in docs:
                        doc.pop("_id", None)
                    if docs:
                        target_collection.insert_many(docs)
            
            response = requests.post(f"{server_url}/api/", json={"db_name":new_db_name},headers={"Content-Type": "application/json"}  ) 

            if response.status_code == 200:
                return Response(
                    {
                        "message": "Modified data restored successfully.",
                        "restored_db": new_db_name,
                        "collection_modified": collection_name,
                        "record_count": len(modified_data),
                        "total_collections": len(source_db.list_collection_names()),
                    },
                    status=status.HTTP_201_CREATED,
                )
            else:
                # API call failed → raise error for Swagger/Client
                try:
                    # Attempt to pass the error message from API
                    error_detail = response.json()
                except Exception:
                    error_detail = {"error": "Unknown error from internal API"}
                return Response(
                    {
                        "message": "Failed to restore data",
                        "api_response": error_detail,
                    },
                    status=response.status_code  
                )

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": str(e)}, status=500)

