import logging

from entities.okta_entities.captchas.captcha_models import CaptchaOrgWideSettings
from entities.okta_entities.captchas.captcha_serializers import CaptchaOrgWideSettingsSerializer
from entities.okta_entities.captchas.views.captcha_base_viewset import BaseCaptchaViewSet

logger = logging.getLogger(__name__)

class CaptchaOrgWideSettingsViewSet(BaseCaptchaViewSet):
    okta_endpoint = "/api/v1/org/captcha"
    entity_type = "okta_captcha_org_wide_settings"
    serializer_class = CaptchaOrgWideSettingsSerializer
    model = CaptchaOrgWideSettings
    
    def extract_data(self, okta_data):
        logger.info("Extracting data from Okta response.")
        extracted_data = [okta_data]

        formatted_data = []
        for record in extracted_data:
            formatted_record = {
                "captcha_id": record.get("captchaId"),
                "enabled_for": record.get("enabledPages"),
            }
            formatted_data.append(formatted_record)
        logger.info(f"Extracted and formatted {len(formatted_data)} group records from Okta.")
        return formatted_data
