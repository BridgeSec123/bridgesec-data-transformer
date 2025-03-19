import os
import json
import requests
from django.http import JsonResponse, FileResponse
from django.conf import settings
from rest_framework import viewsets
from rest_framework.decorators import action
from core.utils.entity_mapping import extract_entity_data, get_unique_field
from core.utils.rate_limit import rate_limit_headers
from datetime import datetime
from bson import ObjectId

class BaseViewSet(viewsets.ModelViewSet):
    """Base viewset for Okta API integration."""
    
    okta_endpoint = ""
    model = None
    serializer_class = None
    entity_type = None
    http_method_names = ["get"]
    
    def fetch_from_okta(self):
        """Fetch data from Okta API dynamically."""
        if not self.okta_endpoint:
            return {"error": "Okta endpoint not defined"}, 500

        okta_url = f"{settings.OKTA_API_URL}/{self.okta_endpoint}"
        API_TOKEN = settings.OKTA_API_TOKEN
        headers = {"Authorization": f"SSWS {API_TOKEN}"}

        response = requests.get(okta_url, headers=headers)
        
        rate_limit = rate_limit_headers(response)

        if response.status_code != 200:
            return {"error": f"Failed to fetch data from Okta API: {response.text}"}, response.status_code

        response_data = response.json()

        return response_data, 200, rate_limit

    def extract_data(self, okta_data):
        """
        Extract relevant data from Okta response using the mapping.
        """
        if not self.entity_type:
            return JsonResponse({"error": "Entity type not defined"}, status=500)

        extracted_data = extract_entity_data(self.entity_type, okta_data)
        return extracted_data

    def store_in_mongodb(self, records):
        """Store entire records dynamically in MongoDB."""
        if not self.model:
            return {"error": "MongoDB model not defined"}, 500

        try:
            valid_records = [record for record in records if record and isinstance(record, dict)]

            if not valid_records:
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

            return {"message": "Data stored/updated successfully"}, 200
        except Exception as e:
            return {"error": str(e)}, 500
    
    @action(detail=False, methods=["get"], url_path="fetch")
    def fetch_data(self, request):
        """Fetch data from Okta, extract it dynamically, and store it."""
        try:
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
            response = FileResponse(open(file_path, "rb"), as_attachment=True, filename=f"{endpoint_name}.json")
            for key, value in rate_headers.items():
                response[key] = value
            return response

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)