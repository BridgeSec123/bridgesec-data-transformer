import logging

from entities.entity_filters import should_skip_network_zone_extraction
from entities.okta_entities.network_zone.network_zone_models import NetworkZone
from entities.okta_entities.network_zone.network_zone_serializer import (
    NetworkZoneSerializer,
)
from entities.views.base_view import BaseEntityViewSet

logger = logging.getLogger(__name__)

class NetworkZoneViewSet(BaseEntityViewSet):
    okta_endpoint = "/api/v1/zones"
    entity_type = "network_zones"
    serializer_class = NetworkZoneSerializer
    model = NetworkZone

    def extract_data(self, okta_data):
        extracted_data = super().extract_data(okta_data)
        formatted_data = []

        for item in extracted_data:
            if not isinstance(item, dict):
                logger.warning(f"Skipping invalid record (not a dict): {item}")
                continue
            zone_name = item.get("name")

            # Skip excluded network zones
            if should_skip_network_zone_extraction(zone_name):
                logger.info("Skipping excluded network zone: %s", zone_name)
                continue

            zone_type = item.get("type")
            record = {
                "network_id": item.get("id"),
                "name": zone_name,
                "type": zone_type,
                "status": item.get("status"),
                "usage": item.get("usage"),
                "system": item.get("system"),
            }

            # Handle IP type fields
            if zone_type == "IP":
                if item.get("gateways"):
                    record["gateways"] = [gateway.get("value") for gateway in item.get("gateways")]
                if item.get("proxies"):
                    record["proxies"] = [proxy.get("value") for proxy in item.get("proxies")]

            # Handle DYNAMIC and DYNAMIC_V2 types
            if zone_type in ["DYNAMIC", "DYNAMIC_V2"]:
                locations = item.get("locations", {})
                if locations:
                    if locations.get("include"):
                        record["dynamic_locations"] = locations.get("include")
                    if zone_type == "DYNAMIC_V2" and locations.get("exclude"):
                        record["dynamic_locations_excluded"] = locations.get("exclude")

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
    
    def fetch_and_store_data(self, db_name, request=None):
        try:

            okta_response, status_code, headers = self.fetch_from_okta(request=request)
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
