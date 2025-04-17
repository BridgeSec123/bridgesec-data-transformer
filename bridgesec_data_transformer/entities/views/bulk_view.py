from datetime import datetime

from core.utils.mongo_utils import ensure_mongo_connection, get_dynamic_db
from django.conf import settings
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from pymongo import MongoClient
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from entities.registry import ENTITY_VIEWSETS
import os
import json


class BulkEntityViewSet(viewsets.ViewSet):
    """Viewset for bulk entity data import."""
    @swagger_auto_schema(
        operation_description="Fetch data from all registered entity APIs and store them in MongoDB",
        responses={201: openapi.Response("Data fetched and stored successfully")},
    )
    def post(self, request):
        # extracted_data_dict = {}
        db_name = get_dynamic_db()
        ensure_mongo_connection(db_name)

        # Loop through all registered entity viewsets dynamically
        for entity_name, viewset_class in ENTITY_VIEWSETS.items():
            viewset_instance = viewset_class()
            
            # Fetch and extract data using the base class methods
            extracted_data = viewset_instance.fetch_and_store_data(db_name)
            if not extracted_data:  # If no data returned
                return Response(
                    {"error": f"Failed to fetch {entity_name} data"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            # Setup output directory
            output_dir = os.path.join(settings.BASE_DIR, "output", db_name)
            os.makedirs(output_dir, exist_ok=True)

            for sub_entity_name, sub_entity_data in extracted_data.items():
                file_name = f"{sub_entity_name}.json"
                file_path = os.path.join(output_dir, file_name)

                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(sub_entity_data, f, ensure_ascii=False, indent=4)
        return Response({
            "message": "Data fetched and stored successfully",
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
    def list_databases(self, request):
        """
        Fetch all database names for a given date.
        """
        date_str = request.query_params.get("date")
        if not date_str:
            return Response({"error": "Missing 'date' parameter"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            
            mongo_client = MongoClient(settings.MONGO_URI)
            all_dbs = mongo_client.list_database_names()
            date_prefix = f"{settings.MONGO_DB_NAME}_{date_str}"
            matching_dbs = [db for db in all_dbs if db.startswith(date_prefix)]
            
            return Response({"databases": matching_dbs}, status=status.HTTP_200_OK)
        except ValueError:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
