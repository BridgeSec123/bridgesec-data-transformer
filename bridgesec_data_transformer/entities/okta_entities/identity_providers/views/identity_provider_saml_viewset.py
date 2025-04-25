import logging

from entities.okta_entities.identity_providers.views.identity_provider_base_viewset import BaseIdentityProviderViewSet
from entities.okta_entities.identity_providers.identity_provider_models import (
    IdentityProviderSAML,
)
from entities.okta_entities.identity_providers.identity_provider_serializers import (
    IdentityProviderSAMLSerializer,
)

logger = logging.getLogger(__name__)

class IdentityProviderSAMLViewSet(BaseIdentityProviderViewSet):
    entity_type = "okta_idp_saml"
    serializer_class = IdentityProviderSAMLSerializer
    model = IdentityProviderSAML

    def extract_data(self, okta_data):
        logger.info("Extracting data from Okta response")
        extracted_data = super().extract_data(okta_data)

        formatted_data = []
        
        for record in extracted_data:
            if record.get("type") == "SAML2":
                protocol = record.get("protocol", {})
                policy = record.get("policy", {})
                endpoints = protocol.get("endpoints", {})
                credentials = protocol.get("credentials", {})
                account_link = policy.get("accountLink", {})
                provisioning = policy.get("provisioning", {})
                algorithms = protocol.get("algorithms", {})
                formatted_record = {
                    "name": record.get("name", ""),
                    "acs_type": endpoints.get("acs", {}).get("type"),
                    "issuer": credentials.get("trust", {}).get("issuer"),
                    "kid": credentials.get("trust", {}).get("kid"),
                    "account_link_action": account_link.get("action"),
                    "account_link_group_include": account_link.get("groupInclude"),
                    "deprovisioned_action": provisioning.get("conditions", {}).get("deprovisioned", {}).get("action", ""),
                    "groups_action": provisioning.get("groups", {}).get("action", ""),
                    "groups_assignments": provisioning.get("groups", {}).get("assignments", []),
                    "groups_attribute": provisioning.get("groups", {}).get("attribute", ""),
                    "groups_filter": provisioning.get("groups", {}).get("filter", []),
                    "issuer_mode": provisioning.get("issuer", {}).get("mode", ""),
                    "max_clock_skew": policy.get("maxClockSkew", ""),
                    "name_format": protocol.get("settings", {}).get("nameFormat", ""),
                    "profile_master": provisioning.get("profileMaster", ""),
                    "provisioning_action": provisioning.get("action", ""),
                    "request_signature_algorithm": algorithms.get("request", {}).get("signature", {}).get("algorithm", ""),
                    "request_signature_scope": algorithms.get("request", {}).get("signature", {}).get("scope", ""),
                    "response_signature_algorithm": algorithms.get("response", {}).get("signature", {}).get("algorithm", ""),
                    "response_signature_scope": algorithms.get("response", {}).get("signature", {}).get("scope", ""),
                    "sso_binding": endpoints.get("sso", {}).get("binding", ""),
                    "sso_destination": endpoints.get("sso", {}).get("destination", ""),
                    "status": record.get("status", ""),
                    "subject_filter": policy.get("subject", {}).get("filter", ""),
                    "subject_format": policy.get("subject", {}).get("format", []),
                    "subject_match_attribute": policy.get("subject", {}).get("matchAttribute", ""),
                    "subject_match_type": policy.get("subject", {}).get("matchType", ""),
                    "suspended_action": provisioning.get("conditions", {}).get("suspended", {}).get("action", ""),
                    "username_template": policy.get("subject", {}).get("userNameTemplate", {}).get("template"),
                }
                formatted_data.append(formatted_record)
        logger.info("Extracted and formatted %d Identity Provider records from Okta", len(formatted_data))
        
        return formatted_data
