import logging

from entities.views.base_view import BaseEntityViewSet
from entities.okta_entities.campaign.campaign_models import Campaign
from entities.okta_entities.campaign.campaign_serializers import CampaignSerializer

logger = logging.getLogger(__name__)


class CampaignViewSet(BaseEntityViewSet):
    okta_endpoint = "/governance/api/v1/campaigns"
    entity_type = "campaigns"
    serializer_class = CampaignSerializer
    model = Campaign

    def extract_data(self, okta_data):
        """Extract and format campaign data from Okta response"""
        formatted_data = []

        # Check if okta_data is a list or single object
        items = okta_data if isinstance(okta_data, list) else [okta_data]

        for item in items:
            formatted_data.append({
                "name": item.get("name", ""),
                "remediation_settings": item.get("remediationSettings", []),
                "resource_settings": item.get("resourceSettings", []),
                "reviewer_settings": item.get("reviewerSettings", []),
                "schedule_settings": item.get("scheduleSettings", {}),
                "notification_settings": item.get("notificationSettings", {}),
                "campaign_tier": item.get("campaignTier", ""),
                "campaign_type": item.get("campaignType", "RESOURCE"),
                "description": item.get("description", ""),
                "principal_scope_settings": item.get("principalScopeSettings", [])
            })

        logger.info("Extracted %d Campaign records", len(formatted_data))
        return formatted_data

    def fetch_and_store_data(self, db_name, request=None):
        try:

            okta_response, status_code, headers = self.fetch_from_okta(request=request)
            logger.info("Fetched Org data from Okta")
            # Step 2: Extract and format data
            extracted_data = self.extract_data(okta_response)
            logger.info("Extracted %d Org records from Okta response", len(extracted_data))

            # Step 3: Store extracted data in MongoDB
            self.store_data(extracted_data, db_name=db_name)
            logger.info("Stored %d Org records in MongoDB database: %s", len(extracted_data), db_name)

            return {"campaigns": extracted_data}

        except Exception as e:
            logger.error("Error in fetch_and_store_data: %s", str(e), exc_info=True)
            return {
                "error": str(e),
                "message": "Failed to fetch and store Org data."
            }
