import logging

from entities.okta_entities.identity_providers.views.identity_provider_base_viewset import BaseIdentityProviderViewSet
from entities.okta_entities.identity_providers.identity_provider_models import (
    IdentityProviderSocial,
)
from entities.okta_entities.identity_providers.identity_provider_serializers import (
    IdentityProviderSocialSerializer,
)

logger = logging.getLogger(__name__)

class IdentityProviderSocialViewSet(BaseIdentityProviderViewSet):
    entity_type = "okta_idp_social"
    serializer_class = IdentityProviderSocialSerializer
    model = IdentityProviderSocial

    def extract_data(self, okta_data):
        logger.info("Extracting data from Okta response")
        extracted_data = super().extract_data(okta_data)

        formatted_data = []
        
        for record in extracted_data:
            if not record.get("type") == "SAML2" and not record.get("type") == "OIDC":
                protocol = record.get("protocol", {})
                policy = record.get("policy", {})
                credentials = protocol.get("credentials", {})
                account_link = policy.get("accountLink", {})
                provisioning = policy.get("provisioning", {})
                formatted_record = {
                    "name": record.get("name", ""),
                    "scopes": protocol.get("scopes", []),
                    "type": record.get("type", ""),
                    "account_link_action": account_link.get("action"),
                    "account_link_group_include": account_link.get("groupInclude"),
                    "apple_kid": credentials.get("apple", {}).get("kid"),
                    "apple_private_key": credentials.get("apple", {}).get("privateKey"),
                    "apple_team_id": credentials.get("apple", {}).get("teamId"),
                    "client_id": credentials.get("client", {}).get("client_id"),
                    "client_secret": credentials.get("client", {}).get("client_secret"),
                    "deprovisioned_action": provisioning.get("conditions", {}).get("deprovisioned", {}).get("action", ""),
                    "groups_action": provisioning.get("groups", {}).get("action", ""),
                    "groups_assignments": provisioning.get("groups", {}).get("assignments", []),
                    "groups_attribute": provisioning.get("groups", {}).get("attribute", ""),
                    "groups_filter": provisioning.get("groups", {}).get("filter", []),
                    "issuer_mode": provisioning.get("issuer", {}).get("mode", ""),
                    "max_clock_skew": policy.get("maxClockSkew", ""),
                    "profile_master": provisioning.get("profileMaster", ""),
                    "protocol_type": protocol.get("type", ""),
                    "provisioning_action": provisioning.get("action", ""),
                    "status": record.get("status", ""),
                    "subject_match_attribute": policy.get("subject", {}).get("matchAttribute", ""),
                    "subject_match_type": policy.get("subject", {}).get("matchType", ""),
                    "suspended_action": provisioning.get("conditions", {}).get("suspended", {}).get("action", ""),
                    "username_template": policy.get("subject", {}).get("userNameTemplate", {}).get("template"),
                }
                formatted_data.append(formatted_record)
        logger.info("Extracted and formatted %d Identity Provider records from Okta", len(formatted_data))
        
        return formatted_data
