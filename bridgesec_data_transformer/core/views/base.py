import json
import logging
import os
from datetime import datetime

import requests
from bson import ObjectId
from django.conf import settings
from django.http import FileResponse, JsonResponse
from rest_framework import viewsets
from rest_framework.decorators import action

from core.utils.entity_mapping import extract_entity_data, get_unique_field
from core.utils.pagination import fetch_all_pages
from core.utils.rate_limit import handle_rate_limit, rate_limit_headers

logger = logging.getLogger(__name__)

class BaseViewSet(viewsets.ViewSet):
    """Base viewset for Okta API integration."""
    
    okta_endpoint = ""
    model = None
    serializer_class = None
    list_serializer_class = None
    entity_type = None
    http_method_names = ["get"]
    
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
        logger.info(f"Extracted {len(extracted_data)} records for entity: {self.entity_type}")
        return extracted_data

    def store_in_mongodb(self, records):
        """Store entire records dynamically in MongoDB."""
        if not self.model:
            logger.error("MongoDB model not defined")
            return {"error": "MongoDB model not defined"}, 500

        try:
            valid_records = [record for record in records if record and isinstance(record, dict)]

            if not valid_records:
                logger.warning("No valid records to store")
                return {"error": "No valid records to store"}, 400

            collection = self.model._get_collection()
            unique_field = get_unique_field(self.entity_type)
            for record in valid_records:
                unique_value = record.get(unique_field)
                if not unique_value:
                    continue
                
                # Check if record already exists
                existing_record = collection.find_one({unique_field: unique_value})
                if not existing_record:
                    # New record: Generate _id and created_at
                    record["_id"] = str(ObjectId())  # Store _id as string
                    record["created_at"] = datetime.now()
                    collection.insert_one(record)  # Insert new record
                else:
                    update_data = record.copy()
                    update_data.pop("_id", None)  # Remove _id to prevent update errors
                    
                    collection.update_one(
                        {unique_field: unique_value},
                        {"$set": update_data}  # Update without modifying _id
                    )
            logger.info("Data stored/updated successfully in MongoDB")
            return {"message": "Data stored/updated successfully"}, 200
        except Exception as e:
            logger.exception("Error while storing data in MongoDB")
            return {"error": str(e)}, 500
    
    @action(detail=False, methods=["get"], url_path="fetch")
    def fetch_data(self, request):
        """Fetch data from Okta, extract it dynamically, and store it."""
        try:
            logger.info("Initiating data fetch from okta and store process")
            okta_data, status, rate_headers = self.fetch_from_okta()
            if status != 200:
                return JsonResponse(okta_data, status=status)

            extracted_data = self.extract_data(okta_data)
            
            serializer = self.serializer_class(extracted_data, many=True)

            output_dir = os.path.join(settings.BASE_DIR, "output")
            os.makedirs(output_dir, exist_ok=True)
            
            endpoint_name = self.okta_endpoint.strip("/").split("/")[-1]
            file_path = os.path.join(output_dir, f"{endpoint_name}.json")
            
            with open(file_path, "w", encoding="utf-8") as json_file:
                json.dump(serializer.data, json_file, indent=4)

            store_result, store_status = self.store_in_mongodb(serializer.data)
            if store_status != 200:
                return JsonResponse(store_result, status=store_status)
            logger.info(f"Fetch and store process completed successfully for {self.entity_type}")
            response = FileResponse(open(file_path, "rb"), as_attachment=True, filename=f"{endpoint_name}.json")
            for key, value in rate_headers.items():
                response[key] = value
            return response

        except Exception as e:
            logger.exception(f"Error in fetch and store process: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)