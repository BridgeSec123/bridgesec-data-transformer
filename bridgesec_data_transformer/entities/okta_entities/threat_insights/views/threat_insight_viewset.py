# entities/okta_entities/sms_templates/sms_template_views.py

import logging
from rest_framework import status
from rest_framework.response import Response

from entities.views.base_view import BaseEntityViewSet
from entities.okta_entities.threat_insights.threat_insight_models import ThreatInsight
from entities.okta_entities.threat_insights.threat_insight_serializer import ThreatInsightSerializer

logger = logging.getLogger(__name__)

class ThreatInsightViewSet(BaseEntityViewSet):
    okta_endpoint = "/api/v1/threats/configuration"
    entity_type = "threat_insights"
    serializer_class = ThreatInsightSerializer
    model = ThreatInsight

    def list(self, request, *args, **kwargs):
        start_date, end_date = super().list(request, *args, **kwargs)

        if not start_date or not end_date:
            templates = self.model.objects()
            logger.info("Retrieved %d Threat InSights", len(templates))
        else:
            templates = self.filter_by_date(start_date, end_date)
            logger.info("Retrieved %d Threat InSights between %s and %s", len(templates), start_date, end_date)

        serializer = self.serializer_class(templates, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def extract_data(self, okta_data):
        # extracted_data = super().extract_data(okta_data)
        formatted_data = []

        # for item in okta_data:
        formatted_data.append({
            "action": okta_data.get("action", ""),
            "network_excludes": okta_data.get("excludeZones", [])
        })
            
        logger.info("Extracted %d Threat InSights records", len(formatted_data))
        return formatted_data
    
    def fetch_and_store_data(self, db_name):
        try:
        # Step 1: Fetch data from Okta
            okta_response, status_code, headers = self.fetch_from_okta()
            logger.info("Fetched Threat InSights data from Okta")

            # Step 2: Extract and format data
            extracted_data = self.extract_data(okta_response)
            logger.info("Extracted %d Threat InSights records from Okta response", len(extracted_data))

            # Step 3: Store extracted data in MongoDB
            self.store_data(extracted_data, db_name=db_name)
            logger.info("Stored %d Threat InSights records in MongoDB database: %s", len(extracted_data), db_name)

            return {"threat_insights": extracted_data}

        except Exception as e:
            logger.error("Error in fetch_and_store_data: %s", str(e), exc_info=True)
            return {
                "error": str(e),
                "message": "Failed to fetch and store Threat InSights data."
            }
