import logging

from rest_framework import status
from rest_framework.response import Response

from entities.okta_entities.inline_hooks.inline_hook_models import InlineHook
from entities.okta_entities.inline_hooks.inline_hook_serializer import InlineHookSerializer
from entities.views.base_view import BaseEntityViewSet

logger = logging.getLogger(__name__)

class InlineHookEntityViewSet(BaseEntityViewSet):
    queryset = InlineHook.objects.all()
    okta_endpoint = "/api/v1/inlineHooks"
    entity_type = "inline_hooks"
    serializer_class = InlineHookSerializer
    model = InlineHook
    
    def list(self, request, *args, **kwargs):
        """Retrieve all records from MongoDB and return serialized data."""
        start_date, end_date = super().list(request, *args, **kwargs)

        if not start_date or not end_date:
            inline_hooks = self.model.objects()  # Fetch all documents using MongoEngine
            logger.info("Retrieved %d inline hooks records from MongoDB", len(inline_hooks))
            
        else:
            inline_hooks = self.filter_by_date(start_date, end_date)
            logger.info(f"Retrieved {len(inline_hooks)} inline hooks between {start_date} and {end_date}")

        inline_hooks_data = []
        for inline_hook in inline_hooks:
            hook_type = ""
            if inline_hook.channel_json:
                hook_type = inline_hook.channel_json.get("type")
            
            if hook_type == "OAUTH":
                inline_hook_data = {
                    "name": inline_hook.name,
                    "version": inline_hook.version,
                    "type": inline_hook.type,
                    "status": inline_hook.status,
                    "channel_json": inline_hook.channel_json,
                }
            
            else:
                inline_hook_data = {
                    "name": inline_hook.name,
                    "version": inline_hook.version,
                    "type": inline_hook.type,
                    "channel": {
                        "version": inline_hook.channel.get("version"),
                        "uri": inline_hook.channel.get("config", {}).get("uri"),
                        "method": inline_hook.channel.get("config", {}).get("method"),
                    },
                    "auth": inline_hook.auth,
                }
                
            inline_hooks_data.append(inline_hook_data)

        logger.info(f"Returning {len(inline_hooks_data)} inline hooks.")
        return Response(inline_hooks_data, status=status.HTTP_200_OK)

    def extract_data(self, okta_data):
        try:
            logger.info("Extracting data from Okta response")
            extracted_data = super().extract_data(okta_data)

            if isinstance(extracted_data, dict) and "error" in extracted_data:
                raise extracted_data
            
            formatted_data = []
            for record in extracted_data:
                channel = record.get("channel", {})
                entity_type = channel.get("type", "").lower()

                formatted_record = {
                    "name": record.get("name", ""),
                    "version": record.get("version", ""),
                    "type": record.get("type", ""),
                }
                
                if entity_type == "http":
                    formatted_record.update({
                        "channel": {
                            "version": channel.get("version", ""),
                            "uri": channel.get("config", {}).get("uri", ""),
                            "method": channel.get("config", {}).get("method", ""),
                        }
                    })
                    
                    auth_scheme = record.get("channel", {}).get("config", {}).get("authScheme", {})
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
                
                elif entity_type == "oauth":
                    formatted_record.update({
                        "status": record.get("status", "ACTIVE"),
                        "channel_json": channel
                    })
                
                formatted_data.append(formatted_record)
            logger.info("Extracted and formatted %d inline hooks records from Okta", len(formatted_data))
            
            return formatted_data
        except Exception as e:
            logger.error("Error extracting data from Okta response: %s", e)
            return e, status.HTTP_500_INTERNAL_SERVER_ERROR
        
    def fetch_and_store_data(self, db_name):
        try:
        # Step 1: Fetch data from Okta
            okta_response, status_code, headers = self.fetch_from_okta()
            logger.info("Fetched Inline Hook data from Okta")

            # Step 2: Extract and format data
            extracted_data = self.extract_data(okta_response)
            logger.info("Extracted %d Inline Hook records from Okta response", len(extracted_data))

            # Step 3: Store extracted data in MongoDB
            self.store_data(extracted_data, db_name=db_name)
            logger.info("Stored %d Inline Hook records in MongoDB database: %s", len(extracted_data), db_name)

            return {"inline_hooks": extracted_data}

        except Exception as e:
            logger.error("Error in fetch_and_store_data: %s", str(e), exc_info=True)
            return {
                "error": str(e),
                "message": "Failed to fetch and store Inline Hook data."
            }

