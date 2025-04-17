import logging

from rest_framework import status
from rest_framework.response import Response

from entities.okta_entities.event_hook.event_hook_models import EventHook
from entities.okta_entities.event_hook.event_hook_serializer import EventHookSerializer
from entities.views.base_view import BaseEntityViewSet

logger = logging.getLogger(__name__)

class EventHookViewSet(BaseEntityViewSet):
    okta_endpoint = "/api/v1/eventHooks"
    entity_type = "event_hooks"
    serializer_class = EventHookSerializer
    model = EventHook
    
    def list(self, request, *args, **kwargs):
        """Retrieve all records from MongoDB and return serialized data."""
        start_date, end_date = super().list(request, *args, **kwargs)

        if not start_date or not end_date:
            event_hooks = self.model.objects()  # Fetch all documents using MongoEngine
            logger.info("Retrieved %d event hooks records from MongoDB", len(event_hooks))
            
        else:
            event_hooks = self.filter_by_date(start_date, end_date)
            logger.info(f"Retrieved {len(event_hooks)} event hooks between {start_date} and {end_date}")

        event_hooks_data = []
        for event_hook in event_hooks:
            event_hook_data = {
                "name": event_hook.name,
                "events": event_hook.events,
                "channel": {
                    "type": event_hook.channel.get("type"),
                    "version": event_hook.channel.get("version"),
                    "uri": event_hook.channel.get("uri"),
                }
            }
            
            # Check if "auth" exists before adding it
            if event_hook.auth:
                event_hook_data["auth"] = {
                    "type": event_hook.auth.get("type"),
                    "key": event_hook.auth.get("key"),
                    "value": event_hook.auth.get("value"),
                }
            event_hooks_data.append(event_hook_data)

        logger.info(f"Returning {len(event_hooks_data)} event hooks.")
        return Response(event_hooks_data, status=status.HTTP_200_OK)

    def extract_data(self, okta_data):
        """
        Override to format the event hook data.
        """
        logger.info("Extracting data from Okta response")
        extracted_data = super().extract_data(okta_data)

        formatted_data = []
        for record in extracted_data: 
            channel = record.get("channel", {})
            formatted_record = {
                "name": record.get("name"),
                "events": record.get("events", {}).get("items", []),
                "channel": {
                    "type": channel.get("type"),
                    "version": channel.get("version"),
                    "uri": channel.get("config").get("uri"),
                }
            }
            auth_scheme = record.get("channel", {}).get("config", {}).get("authScheme")
            if auth_scheme:
                formatted_record["auth"] = {
                    "type": auth_scheme.get("type")
                }

            # Extract headers (if present) from channel → config → headers
            headers = record.get("channel", {}).get("config", {}).get("headers", [])
            if headers:
                for header in headers:
                    if "auth" not in formatted_record:
                        formatted_record["auth"] = {}
                    for key, value in header.items():
                        formatted_record["auth"][key] = value
                    formatted_record["auth"]["value"] = header.get("value")
                    
            
            formatted_data.append(formatted_record)
        logger.info("Extracted and formatted %d event hook records from Okta", len(formatted_data))
        
        return formatted_data

    def fetch_and_store_data(self, db_name):
        try:
        # Step 1: Fetch data from Okta
            okta_response, status_code, headers = self.fetch_from_okta()
            logger.info("Fetched Event Hook data from Okta")

            # Step 2: Extract and format data
            extracted_data = self.extract_data(okta_response)
            logger.info("Extracted %d Event Hook records from Okta response", len(extracted_data))

            # Step 3: Store extracted data in MongoDB
            self.store_data(extracted_data, db_name=db_name)
            logger.info("Stored %d Event Hook records in MongoDB database: %s", len(extracted_data), db_name)

            return {"event_hooks": extracted_data}

        except Exception as e:
            logger.error("Error in fetch_and_store_data: %s", str(e), exc_info=True)
            return {
                "error": str(e),
                "message": "Failed to fetch and store Event Hook data."
            }
