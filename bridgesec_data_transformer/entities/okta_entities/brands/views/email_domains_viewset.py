import logging
import requests
from django.conf import settings

from entities.okta_entities.brands.views.brand_base_viewset import BaseBrandViewSet
from core.utils.pagination import fetch_all_pages
from core.utils.rate_limit import handle_rate_limit, rate_limit_headers
from entities.okta_entities.brands.brand_models import EmailDomain
from entities.okta_entities.brands.brand_serializers import EmailDomainSerializer 


logger = logging.getLogger(__name__)

class EmailDomainViewset(BaseBrandViewSet):
    """
    ViewSet for managing EmailDomain entities fetched from Okta and stored in MongoDB.
    """
    okta_endpoint = "api/v1/email-domains"
    entity_type = "okta_email_domain"
    serializer_class = EmailDomainSerializer
    model = EmailDomain

    def extract_data(self, okta_data, brand_id=None):
        """
        Extract and format the email domain records from Okta response.
        """
        logger.info("Extracting and formatting email domain data.")
        extracted_data = super().extract_data(okta_data)

        formatted_data = []
        for record in extracted_data:
            formatted_record = {
                "brand_id": brand_id,
                "domain": record.get("domain", ""),
                "display_name": record.get("displayName", ""),
                "user_name": record.get("userName", ""),
            }
            formatted_data.append(formatted_record)

        logger.info(f"Formatted {len(formatted_data)} email domain records.")
        return formatted_data


