import logging

import requests
from rest_framework import status
from rest_framework.response import Response
from django.conf import settings

from entities.okta_entities.policies.policy_models import PolicyMFA
from entities.okta_entities.policies.views.policy_base_viewset import BasePolicyViewSet
from entities.okta_entities.policies.policy_serializers import PolicyMFASerializer
from core.utils.pagination import fetch_all_pages
from core.utils.rate_limit import handle_rate_limit, rate_limit_headers
logger = logging.getLogger(__name__)

class PolicyMFAViewSet(BasePolicyViewSet):
    okta_endpoint = "/api/v1/policies"
    entity_type = "okta_policy_mfa"
    serializer_class = PolicyMFASerializer
    model = PolicyMFA
    
    def fetch_from_okta(self):
        """Fetch data from Okta API dynamically."""
        if not self.okta_endpoint:
            logger.error("Okta endpoint not defined")
            return {"error": "Okta endpoint not defined"}, 500

        okta_url = f"{settings.OKTA_API_URL}/{self.okta_endpoint}"
        headers = {"Authorization": f"SSWS {settings.OKTA_API_TOKEN}"}
        
        params = {
            "type": "MFA_ENROLL"
        }
        
        logger.info(f"Fetching data from Okta endpoint: {self.okta_endpoint}")
        
        while True:  # Keep retrying if rate limited
            response = requests.get(okta_url, headers=headers, params=params)

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
                return all_data, 200, rate_limit_headers(response)

            return response_data, 200, rate_limit_headers(response)
    
    def extract_data(self, okta_data):
        """
        Override to format the user data by removing the "profile" key.
        """
        logger.info("Extracting data from Okta response")
        extracted_data = super().extract_data(okta_data)

        formatted_data = []
        # allowed_fields = set(User._fields.keys())

        for record in extracted_data:
            groups = record.get("conditions", {}).get("people", {}).get("groups", [])
            factors = record.get("settings", {}).get("factors", [])

            formatted_record = {
                "name": record.get("name"),
                "description": record.get("description"),
                "duo": record.get("duo"),
                "external_idps": record.get("external_idps"),
                "fido_u2f": record.get("fido_u2f"),
                "fido_webauthn": record.get("fido_webauthn"),
                "google_otp": record.get("google_otp"),
                "groups_included": groups.get("include"),
                "hotp": record.get("hotp"),
                "is_oie": record.get("is_oie"),
                "okta_call": record.get("okta_call"),
                "okta_email": record.get("okta_email"),
                "okta_otp": factors.get("okta_otp").get("enroll", {}),
                "okta_password": factors.get("okta_password").get("enroll", {}),
                "okta_push": record.get("okta_push"),
                "okta_question": record.get("okta_question"),
                "okta_sms": record.get("okta_sms"),
                "okta_verify": record.get("okta_verify"),
                "onprem_mfa": record.get("onprem_mfa"),
                "phone_number": record.get("phone_number"),
                "priority": record.get("priority"),
                "rsa_token": record.get("rsa_token"),
                "security_question": record.get("security_question"),
                "status": record.get("status"),
                "symantec_vip": record.get("symantec_vip"),
                "web_authn": record.get("web_authn"),
                "yubikey_token": record.get("yubikey_token"),
            }
            formatted_data.append(formatted_record)

        logger.info("Final extracted %d user records after formatting and filtering", len(formatted_data))
        return formatted_data
