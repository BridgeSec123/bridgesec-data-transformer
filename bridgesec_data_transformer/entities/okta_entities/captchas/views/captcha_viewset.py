import logging

from entities.okta_entities.captchas.captcha_models import Captcha
from entities.okta_entities.captchas.captcha_serializers import CaptchaSerializer
from entities.okta_entities.captchas.views.captcha_base_viewset import (
    BaseCaptchaViewSet,
)

logger = logging.getLogger(__name__)

class CaptchaViewSet(BaseCaptchaViewSet):
    okta_endpoint = "/api/v1/captchas"
    entity_type = "okta_captcha"
    serializer_class = CaptchaSerializer
    model = Captcha
    
    def extract_data(self, okta_data):
        logger.info("Extracting data from Okta response.")
        extracted_data = super().extract_data(okta_data)

        formatted_data = []
        for record in extracted_data:
            formatted_record = {
                "name": record.get("name", ""),
                "type": record.get("type", ""),
                "site_key": record.get("siteKey", ""),
                "secret_key ": record.get("secret_key", ""),
            }
            formatted_data.append(formatted_record)
        logger.info(f"Extracted and formatted {len(formatted_data)} group records from Okta.")
        return formatted_data