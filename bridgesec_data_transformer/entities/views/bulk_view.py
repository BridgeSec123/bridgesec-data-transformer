import json
import os
import re
from datetime import datetime, timedelta


from entities.serializers.restore_serializer import RestoreDataSerializer
from core.utils.collection_mapping import RESOURCE_COLLECTION_MAP
from core.utils.mongo_utils import get_dynamic_db, ensure_mongo_connection
from core.utils.db_utils import extract_time, get_collection_name, get_latest_db
from django.conf import settings
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from pymongo import MongoClient
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from core.tasks.bulk_tasks import run_bulk_entity_task
from celery import shared_task

from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from core.authentication import CustomJWTAuthentication
from entities.registry import ENTITY_VIEWSETS
from entities.services.resouce_data_service import EntityDataService
import requests
import logging

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
        Fetch data from Mongo using pymongo → no ensure_mongo_connection needed.
        """
        if not date_str or not entity_name:
            return Response(
                {"error": "Missing 'date' or 'entity_type' parameter"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            datetime.strptime(date_str, "%Y-%m-%d")

            service = EntityDataService()
            data = service.fetch(date_str, entity_name)

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

            if collection_name in source_db.list_collection_names():
                source_collection = source_db[collection_name]
                target_collection = new_db[collection_name]

                for doc in modified_data:
                    doc.pop("_id", None)

                if modified_data:
                    target_collection.insert_many(modified_data)
                
            tf_response = requests.post(f"{server_url}/api/", json={"db_name":new_db_name, "collection_name": collection_name},headers={"Content-Type": "application/json"}  ) 

            try:
                tf_data = tf_response.json()
            except Exception:
                tf_data = {"message": "Unknown response from TF repo"}

                # extract message
            tf_message = tf_data.get("message", "No message returned")
            
            for coll in source_db.list_collection_names():
                if coll == collection_name:
                    continue  # already handled
                source_collection = source_db[coll]
                target_collection = new_db[coll]

                docs = list(source_collection.find({}, {"_id": 0}))
                if docs:
                    target_collection.insert_many(docs)

            return Response(
                {
                    "tf_message": tf_message,
                    "message": "Modified data restored successfully.",
                    "restored_db": new_db_name,
                    "collection_modified": collection_name,
                    "record_count": len(modified_data),
                    "total_collections": len(source_db.list_collection_names()),
                },
                status=status.HTTP_201_CREATED,
            )
            

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": str(e)}, status=500)

