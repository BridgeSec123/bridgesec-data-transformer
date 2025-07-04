import json
import os
import re
from datetime import datetime

from core.tasks.bulk_tasks import run_bulk_entity_task
from core.utils.collection_mapping import RESOURCE_COLLECTION_MAP
from core.utils.mongo_utils import ensure_mongo_connection, get_dynamic_db
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
from entities.registry import ENTITY_VIEWSETS


class BulkEntityViewSet(viewsets.ViewSet):
    # authentication_classes = [JWTAuthentication]
    # permission_classes = [IsAuthenticated]
    """Viewset for bulk entity data import."""
    def post(self, request):
        db_name = get_dynamic_db()
        ensure_mongo_connection(db_name)
        run_bulk_entity_task.delay(db_name)
       
        return Response({
            "message": "Task Triggered",
            "db_name": db_name
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=["get"], url_path="fetch-stored-data")
    def fetch_stored_data(self, request):
        """
        Fetch stored data from MongoDB based on date and entity type.
        """
        date_str = request.query_params.get("date")
        entity_type = request.query_params.get("entity")

        if not date_str or not entity_type:
            return Response({"error": "Missing 'date' or 'entity' parameter"}, status=status.HTTP_400_BAD_REQUEST)

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

            model_class = ENTITY_VIEWSETS.get(entity_type)
            if not model_class:
                return Response({"error": "Invalid entity type"}, status=status.HTTP_400_BAD_REQUEST)
            
            viewset_instance = model_class()
            data = list(viewset_instance.model.objects.using(latest_db).all().as_pymongo())
            for record in data:
                record.pop("_id", None)

            return Response(data, status=status.HTTP_200_OK)

        except ValueError:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD"}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    @action(detail=False, methods=["get"], url_path="list-databases")
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'date', openapi.IN_QUERY, description="Date for which to fetch databases (YYYY-MM-DD)", type=openapi.TYPE_STRING
            )
        ]
    )
    def list_databases(self, request):
        """
        Fetch all database names, optionally filtered by a given date (YYYY-MM-DD).
        """
        selected_date = request.query_params.get("date")  # e.g., "2024-06-05"
        if not selected_date:
            return Response({"error": "date is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            
            db_date_pattern = selected_date.replace("-", "_")

            client = MongoClient(settings.MONGO_URI)
            db_names = client.list_database_names()

            time_list = []
            pattern = re.compile(rf"bridgesec_{db_date_pattern}T(\d{{4}})")
            for db_name in db_names:
                match = pattern.match(db_name)
                if match:
                    raw_time = match.group(1)  # e.g., '2000'
                    formatted_time = f"{raw_time[:2]}:{raw_time[2:]}"  # -> '20:00'
                    time_list.append(formatted_time)

            return Response((sorted(time_list)))
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'entity_type',
                openapi.IN_QUERY,
                description="Optional. If provided, returns sub-entities for this entity type.",
                type=openapi.TYPE_STRING
            )
        ]
    )

    @action(detail=False, methods=["get"], url_path="resource-names")
    def get_resource_names(self, request):
        """
        - If `entity_type` is provided in query params, return its sub-entities.
        - Else return all available resource names (main entity types).
        """
        try:
            entity_type = request.query_params.get("entity_type")

            if entity_type:
                entity_type = entity_type.title()
                sub_entities = RESOURCE_COLLECTION_MAP.get(entity_type)

                if not sub_entities:
                    return Response(
                        {"detail": f"No sub-entities found for entity type '{entity_type}'"},
                        status=status.HTTP_404_NOT_FOUND
                    )

                display_names = [entry["label"] for entry in sub_entities]
                return Response((display_names), status=status.HTTP_200_OK)

            # No query param provided, return all entity types
            resource_names = sorted(RESOURCE_COLLECTION_MAP.keys())
            return Response({"entity_types": resource_names}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=["get"], url_path=r"data/(?P<db_name>[^/.]+)/(?P<resource_name>[^/.]+)")
    def get_resource_data(self, request, db_name, resource_name):
        """
        Fetch data for a given resource from a specific MongoDB database.
        """
        try:
            collections = RESOURCE_COLLECTION_MAP.get(resource_name)
            if not collections:
                return Response({"error": f"Invalid or unsupported resource: {resource_name}"}, status=status.HTTP_400_BAD_REQUEST)

            mongo_client = MongoClient(settings.MONGO_URI)
            db = mongo_client[db_name]

            merged_data = []
            for collection_name in collections:
                if collection_name in db.list_collection_names():
                    docs = list(db[collection_name].find({}, {'_id': 0}))  # omit MongoDB _id
                    merged_data.extend(docs)

            return Response(merged_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)