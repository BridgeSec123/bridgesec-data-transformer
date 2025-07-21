import json
import os
import re
from datetime import datetime

from entities.serializers.restore_serializer import RestoreDataSerializer
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
from core.authentication import CustomJWTAuthentication
from entities.registry import ENTITY_VIEWSETS

def extract_time(db_name):
    try:
        time_part = db_name.split('T')[1]
        return f"{time_part[:2]}:{time_part[2:]}"
    except Exception:
        return None 
    
class BulkEntityViewSet(viewsets.ViewSet):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = RestoreDataSerializer
    
    """Viewset for bulk entity data import."""
    def post(self, request):
        db_name = get_dynamic_db()
        ensure_mongo_connection(db_name)
        run_bulk_entity_task.delay(db_name)
       
        return Response({
            "message": "Task Triggered",
            "db_name": db_name
        },status=status.HTTP_201_CREATED)
    
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
        date_str = request.query_params.get("date")

        try:
            mongo_client = MongoClient(settings.MONGO_URI)
            all_dbs = mongo_client.list_database_names()

            if date_str:
                try:
                    datetime.strptime(date_str, "%Y-%m-%d")  # validate format
                    date_prefix = f"{settings.MONGO_DB_NAME}_{date_str}"
                    all_dbs = [db for db in all_dbs if db.startswith(date_prefix)]
                except ValueError:
                    return Response({"error": "Invalid date format. Use YYYY-MM-DD"}, status=status.HTTP_400_BAD_REQUEST)
                
            db_dict = {
                extract_time(db): db
                for db in all_dbs
                if extract_time(db)
            }

            return Response(db_dict, status=status.HTTP_200_OK)

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

                display_names = [value for entry in sub_entities for value in entry.keys()]

                return Response({"data":display_names}, status=status.HTTP_200_OK)

            # No query param provided, return all entity types
            resource_names = sorted(RESOURCE_COLLECTION_MAP.keys())
            return Response({"data": resource_names}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(
        detail=False,
        methods=["get"],
        url_path=r"data/(?P<date_str>\d{4}-\d{2}-\d{2})/(?P<entity_name>[^/.]+)"
    )
    def get_resource_data(self, request, date_str, entity_name):
        """
        Fetch data from latest matching DB for a given entity and date via path parameters.
        """
        if not date_str or not entity_name:
         return Response(
            {"error": "Missing 'date' or 'entity_type' parameter"},
            status=status.HTTP_400_BAD_REQUEST
        )

        try:
            #  Validate the date format
            try:
                datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                return Response(
                    {"error": "Invalid date format. Use YYYY-MM-DD"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Connect to MongoDB and list all databases
            mongo_client = MongoClient(settings.MONGO_URI)
            all_dbs = mongo_client.list_database_names()

            # Filter DBs with date prefix
            date_prefix = f"{settings.MONGO_DB_NAME}_{date_str}"
            matching_dbs = [db for db in all_dbs if db.startswith(date_prefix)]

            if not matching_dbs:
              return Response(
                {
                    "message": f"No matching databases found for the given date: {date_str}",
                    "data": []
               },
              status=status.HTTP_200_OK
              )

            # Get the latest DB (last in sorted list)
            latest_db_name = matching_dbs[-1]

            # Get collection name for entity_type
            collection_name = None
            for group in RESOURCE_COLLECTION_MAP.values():
                for mapping in group:
                    if entity_name in mapping:
                        collection_name = mapping[entity_name]
                        break
                if collection_name:
                    break

            if not collection_name:
                return Response(
                  {
                    "message": f"Entity type '{entity_name}' not found in resource map.You are entering a wrong entity_type",
                    "data": []
                  },
                status=status.HTTP_200_OK
            )

            # Fetch data from the latest db + collection
            db = mongo_client[latest_db_name]
            collection = db[collection_name]

            data = list(collection.find({}, {"_id": 0}))  # exclude _id

            return Response(data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @swagger_auto_schema(
        method="post",
        request_body=RestoreDataSerializer,
        responses={201: "Success", 400: "Bad Request"}
    )
    @action(
        detail=False,
        methods=["post"],
        url_path=r"restore/(?P<date_str>\d{4}-\d{2}-\d{2})/(?P<entity_name>[^/.]+)"
    )
    def restore_modified_data(self, request, date_str, entity_name):
        try:
            serializer = RestoreDataSerializer(data=request.data)  
            if not serializer.is_valid():
                return Response(serializer.errors, status=400)

            modified_data = serializer.validated_data["data"]

            collection_name = None
            for group in RESOURCE_COLLECTION_MAP.values():
                for mapping in group:
                    if entity_name in mapping:
                        collection_name = mapping[entity_name]
                        break
                if collection_name:
                    break

            if not collection_name:
                return Response(
                  {
                    "message": f"Entity type '{entity_name}' not found in resource map.You are entering a wrong entity_type",
                    "data": []
                  },
                status=status.HTTP_200_OK
            )

            new_db_name = get_dynamic_db()
            ensure_mongo_connection(new_db_name)

            # Connect and insert modified data
            mongo_client = MongoClient(settings.MONGO_URI)
            target_collection = mongo_client[new_db_name][collection_name]

            for doc in modified_data:
                doc.pop("_id", None)

            target_collection.insert_many(modified_data)

            return Response({
                "message": "Modified data restored successfully.",
                "restored_db": new_db_name,
                "collection": collection_name,
                "record_count": len(modified_data)
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": str(e)}, status=500)









