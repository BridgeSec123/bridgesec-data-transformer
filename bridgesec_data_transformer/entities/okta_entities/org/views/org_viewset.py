import logging

from rest_framework import status
from rest_framework.response import Response

from entities.okta_entities.org.org_models import Org
from entities.okta_entities.org.org_serializers import OrgSerializer
from entities.views.base_view import BaseEntityViewSet

logger = logging.getLogger(__name__)

class OrgViewSet(BaseEntityViewSet):
    okta_endpoint = "/api/v1/org"
    entity_type = "orgs"
    serializer_class = OrgSerializer
    model = Org
    
    def list(self, request, *args, **kwargs):
        """Retrieve all records from MongoDB and return serialized data."""
        start_date, end_date = super().list(request, *args, **kwargs)

        if not start_date or not end_date:
            orgs = self.model.objects()  # Fetch all documents using MongoEngine
            logger.info("Retrieved %d org records from MongoDB", len(orgs))
            
        else:
            orgs = self.filter_by_date(start_date, end_date)
            logger.info(f"Retrieved {len(orgs)} orgs between {start_date} and {end_date}")

        orgs_data = []
        for org in orgs:    
            serializer = self.serializer_class(org)
            orgs_data.append(serializer.data)

        logger.info(f"Returning {len(orgs_data)} orgs.")
        return Response(orgs_data, status=status.HTTP_200_OK)
    
    def extract_data(self, okta_data):
        """ Extract data from Okta API response. """
        logger.info("extracting data from Okta API response for entity type orgs")
        formatted_data = [{
            "company_name": okta_data.get("companyName"),
            "website": okta_data.get("website"),
            "address1": okta_data.get("address1"),
            "address2": okta_data.get("address2"),
            "billing_contact_user": okta_data.get("billing_contact_user"),
            "city": okta_data.get("city"),
            "country": okta_data.get("country"),
            "end_user_support_help_url": okta_data.get("endUserSupportHelpURL"),
            "logo": okta_data.get("logo"),
            "opt_out_communication_emails": okta_data.get("opt_out_communication_emails"),
            "phone_number": okta_data.get("phoneNumber"),
            "postal_code": okta_data.get("postalCode"),
            "state": okta_data.get("state"),
            "support_phone_number": okta_data.get("supportPhoneNumber"),
            "technical_contact_user": okta_data.get("technical_contact_user")
        }]
        logger.info(f"Extracted {len(formatted_data)} records for entity type {self.entity_type}")
        return formatted_data

    def fetch_and_store_data(self, db_name):
        try:
            
            okta_response, status_code, headers = self.fetch_from_okta()
            logger.info("Fetched Org data from Okta")
            # Step 2: Extract and format data
            extracted_data = self.extract_data(okta_response)
            logger.info("Extracted %d Org records from Okta response", len(extracted_data))

            # Step 3: Store extracted data in MongoDB
            self.store_data(extracted_data, db_name=db_name)
            logger.info("Stored %d Org records in MongoDB database: %s", len(extracted_data), db_name)

            return {"orgs": extracted_data}

        except Exception as e:
            logger.error("Error in fetch_and_store_data: %s", str(e), exc_info=True)
            return {
                "error": str(e),
                "message": "Failed to fetch and store Org data."
            }