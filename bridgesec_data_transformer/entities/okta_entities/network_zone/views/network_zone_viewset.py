import logging
from rest_framework import status
from rest_framework.response import Response

from entities.views.base_view import BaseEntityViewSet
from entities.okta_entities.network_zone.network_zone_models import NetworkZone
from entities.okta_entities.network_zone.network_zone_serializer import NetworkZoneSerializer

logger = logging.getLogger(__name__)

class NetworkZoneViewSet(BaseEntityViewSet):
    okta_endpoint = "/api/v1/zones"
    entity_type = "network_zones"
    serializer_class = NetworkZoneSerializer
    model = NetworkZone

    def list(self, request, *args, **kwargs):
        start_date, end_date = super().list(request, *args, **kwargs)

        if not start_date or not end_date:
            templates = self.model.objects()
            logger.info("Retrieved %d network zones", len(templates))
        else:
            templates = self.filter_by_date(start_date, end_date)
            logger.info("Retrieved %d network zones between %s and %s", len(templates), start_date, end_date)

        serializer = self.serializer_class(templates, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def extract_data(self, okta_data):
        extracted_data = super().extract_data(okta_data)
        formatted_data = []

        for item in extracted_data:
            zone_type = item.get("type")
            record = {
                "name": item.get("name"),
                "type": zone_type,
                "status": item.get("status"),
                "usage": item.get("usage"),
            }

            # Handle IP type fields
            if zone_type == "IP":
                if item.get("gateways"):
                    record["gateways"] = item.get("gateways")
                if item.get("proxies"):
                    record["proxies"] = item.get("proxies")

            # Handle DYNAMIC and DYNAMIC_V2 types
            if zone_type in ["DYNAMIC", "DYNAMIC_V2"]:
                locations = item.get("locations", {})
                if locations:
                    if locations.get("include"):
                        record["dynamic_locations"] = locations.get("include")
                    if zone_type == "DYNAMIC_V2" and locations.get("exclude"):
                        record["dynamic_locations_exclude"] = locations.get("exclude")

                ip_services = item.get("ipServiceCategories", {})
                if ip_services:
                    if ip_services.get("include"):
                        record["ip_service_categories_include"] = ip_services.get("include")
                    if ip_services.get("exclude"):
                        record["ip_service_categories_exclude"] = ip_services.get("exclude")

                asns = item.get("asns", {}).get("include")
                if asns:
                    record["asns"] = asns

                if zone_type == "DYNAMIC" and item.get("dynamicProxyType"):
                    record["dynamic_proxy_type"] = item.get("dynamicProxyType")

            formatted_data.append(record)

        logger.info("Extracted %d network zone records", len(formatted_data))
        return formatted_data
    
    def fetch_and_store_data(self, db_name):
        try:
            
            okta_response, status_code, headers = self.fetch_from_okta()
            logger.info("Fetched network zone data from Okta")
            # Step 2: Extract and format data
            extracted_data = self.extract_data(okta_response)
            logger.info("Extracted %d Network zone records from Okta response", len(extracted_data))

            # Step 3: Store extracted data in MongoDB
            self.store_data(extracted_data, db_name=db_name)
            logger.info("Stored %d Network zone records in MongoDB database: %s", len(extracted_data), db_name)

            return {"network_zones": extracted_data}

        except Exception as e:
            logger.error("Error in fetch_and_store_data: %s", str(e), exc_info=True)
            return {
                "error": str(e),
                "message": "Failed to fetch and store network zone data."
            }
