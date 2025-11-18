import logging

from entities.services.service_utils import fetch_collection

logger = logging.getLogger(__name__)


class AuthServer:
    """
    Builds nested JSON per Auth Server with scopes, claims, policies, and rules.
    Fetches data directly from DB collections without merging.
    """

    def build(self, db):
        logger.info("Fetching Auth Server data from DB...")

        # Fetch parent auth servers from DB
        auth_servers = fetch_collection(db, "okta_auth_server")
        logger.info(f"Found {len(auth_servers)} auth servers")

        # Fetch all child collections from DB
        scopes = fetch_collection(db, "okta_auth_server_scope")
        claims = fetch_collection(db, "okta_auth_server_claim")
        policies = fetch_collection(db, "okta_auth_server_policy")
        rules = fetch_collection(db, "okta_auth_server_policy_rule")
        trusted_servers = fetch_collection(db, "okta_trusted_server")

        logger.info(f"Found {len(scopes)} scopes, {len(claims)} claims, {len(policies)} policies, {len(rules)} rules, {len(trusted_servers)} trusted servers")

        # Build nested structure
        results = []
        for server in auth_servers:
            server_id = server.get("auth_server_id")

            formatted = {
                **server,  # Include all server fields
                "authorization_server_scopes": [scope for scope in scopes if scope.get("auth_server_id") == server_id],
                "authorization_server_claims": [claim for claim in claims if claim.get("auth_server_id") == server_id],
                "authorization_server_accessPolicies": [policy for policy in policies if policy.get("auth_server_id") == server_id],
                "authorization_server_accessPoliciesRules": [rule for rule in rules if rule.get("auth_server_id") == server_id],
                "authorization_server_trusted_servers": [trusted for trusted in trusted_servers if trusted.get("auth_server_id") == server_id],
            }

            logger.info(f"Auth server {server_id} has {len(formatted['authorization_server_scopes'])} scopes, {len(formatted['authorization_server_claims'])} claims, {len(formatted['authorization_server_accessPolicies'])} policies, {len(formatted['authorization_server_accessPoliciesRules'])} rules")
            results.append(formatted)

        logger.info(f"Built nested Auth Server data for {len(results)} servers")
        return results
