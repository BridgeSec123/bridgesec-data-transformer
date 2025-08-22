import logging

import requests
from core.utils.pagination import fetch_all_pages
from core.utils.rate_limit import handle_rate_limit, rate_limit_headers
from django.conf import settings

from entities.okta_entities.policies.policy_models import PolicyPassword
from entities.okta_entities.policies.policy_serializers import PolicyPasswordSerializer
from entities.okta_entities.policies.views.policy_base_viewset import BasePolicyViewSet

logger = logging.getLogger(__name__)


class PolicyPasswordViewSet(BasePolicyViewSet):
    okta_endpoint = "/api/v1/policies"
    entity_type = "okta_policy_password"
    serializer_class = PolicyPasswordSerializer
    model = PolicyPassword
    
    def fetch_from_okta(self):
        """Fetch data from Okta API dynamically."""
        if not self.okta_endpoint:
            logger.error("Okta endpoint not defined")
            return {"error": "Okta endpoint not defined"}, 500

        okta_url = f"{settings.OKTA_API_URL}/{self.okta_endpoint}"
        headers = {"Authorization": f"SSWS {settings.OKTA_API_TOKEN}"}
        
        params = {
            "type": "PASSWORD"
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

        for record in extracted_data:
            conditions = record.get("conditions", {})
            factors = record.get("settings", {}).get("recovery", {}).get("factors", {})
            password = record.get("settings", {}).get("password",{})
            complexity = password.get("complexity",{})
            age = password.get("age")
            lockout = password.get("lockout")
            recovery_question = factors.get("recovery_question", {})
            okta_email = factors.get("okta_email", {})
            formatted_record = {
                "id": record.get("id"),
                "name": record.get("name"),
                "auth_provider": conditions.get("authProvider", {}).get("provider", ""),
                "call_recovery": factors.get("okta_call", {}).get("status", ""),
                "description": record.get("description"),
                "email_recovery": okta_email.get("status", ""),
                "groups_included": conditions.get("people", {}).get("groups", {}).get("included", []),
                "password_auto_unlock_minutes": complexity.get("lockout",{}).get("autoUnlockMinutes", 0),
                "password_dictionary_lookup": complexity.get("dictionary", {}).get("common", {}).get("exclude"),
                "password_exclude_first_name": complexity.get("password", {}).get("excludeFirstName",""),
                "password_exclude_last_name": complexity.get("password", {}).get("excludeLastName",""),
                "password_exclude_username": complexity.get("password", {}).get("excludeUsername",""),
                "password_expire_warn_days": age.get("expireWarnDays", 0),
                "password_history_count": age.get("historyCount", 0),
                "password_lockout_notification_channels": lockout.get("userLockoutNotificationChannels", []),
                "password_max_age_days": age.get("maxAgeDays", 0),
                "password_max_lockout_attempts": lockout.get("maxAttempts", 0),
                "password_min_age_minutes": age.get("minAgeMinutes", 0),
                "password_min_length": complexity.get("minLength", 0),
                "password_min_lowercase": complexity.get("minLowerCase", 0),   
                "password_min_number": complexity.get("minNumber", 0),
                "password_min_symbol": complexity.get("minSymbol", 0),
                "password_min_uppercase": complexity.get("minUpperCase"),
                "password_show_lockout_failures": lockout.get("showLockoutFailures"),
                "priority": record.get("priority"),
                "question_min_length": recovery_question.get("properties", {}).get("complexity", {}).get("minLength"),
                "question_recovery": recovery_question.get("status", ""),
                "recovery_email_token": okta_email.get("properties", {}).get("recoveryToken", {}).get("tokenLifetimeMinutes"),
                "skip_unlock": complexity.get("lockout",{}).get("skipUnlock", False),
                "sms_recovery": factors.get("okta_sms", {}).get("status", ""),
                "status": record.get("status"),
            }
            formatted_data.append(formatted_record)

        logger.info("Final extracted %d user records after formatting and filtering", len(formatted_data))
        return formatted_data


