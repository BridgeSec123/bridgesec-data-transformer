import logging
import requests
from django.conf import settings

from entities.okta_entities.brands.views.brand_base_viewset import BaseBrandViewSet
from core.utils.pagination import fetch_all_pages
from core.utils.rate_limit import handle_rate_limit, rate_limit_headers
from entities.okta_entities.brands.brand_models import OktaTheme
from entities.okta_entities.brands.brand_serializers import OktaThemeSerializer


logger = logging.getLogger(__name__)

class ThemeViewset(BaseBrandViewSet):
    """
    ViewSet for managing EmailDomain entities fetched from Okta and stored in MongoDB.
    """
    okta_endpoint = "/api/v1/brands/{brandId}/themes"
    entity_type = "okta_theme"
    serializer_class = OktaThemeSerializer
    model = OktaTheme

    def fetch_from_okta(self, brand_id):
        if not brand_id:
            logger.error("Brand ID is required to fetch memberships.")
            return []

        if not self.okta_endpoint:
            logger.error("Okta endpoint not defined")
            return {"error": "Okta endpoint not defined"}, 500

        okta_url = f"{settings.OKTA_API_URL}/{self.okta_endpoint.format(brandId=brand_id)}"
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
                return all_data

            return response_data
    
    def extract_data(self, okta_data, brand_id=None):
        """
        Extract and format the email domain records from Okta response.
        """
        if not brand_id:
            logger.warning("No brand ID provided, skipping theme fetch")
            return []
        
        logger.info("Extracting and formatting customization domain  data.")
        extracted_data = super().extract_data(okta_data)

        formatted_data = []
        for record in extracted_data:
            formatted_record = {
                "brand_id": brand_id,
                "background_image": record.get("backgroundImage"),
                "email_template_touch_point_variant": record.get("emailTemplateTouchPointVariant"),
                "end_user_dashboard_touch_point_variant": record.get("endUserDashboardTouchPointVariant"),
                "error_page_touch_point_variant": record.get("errorPageTouchPointVariant"),
                "favicon": record.get("favicon"),
                "logo": record.get("logo"),
                "primary_color_contrast_hex": record.get("primaryColorContrastHex"),
                "primary_color_hex": record.get("primaryColorHex"),
                "secondary_color_contrast_hex": record.get("secondaryColorContrastHex"),
                "secondary_color_hex": record.get("secondaryColorHex"),
                "sign_in_page_touch_point_variant": record.get("signInPageTouchPointVariant"),
                "theme_id": record.get("id"),
            }
            formatted_data.append(formatted_record)

        logger.info(f"Formatted {len(formatted_data)} customization theme records.")
        return formatted_data