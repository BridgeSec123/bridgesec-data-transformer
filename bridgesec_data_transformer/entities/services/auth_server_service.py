from typing import Dict, Any, List, Optional
from pymongo import MongoClient
from django.conf import settings
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import utility functions from core.utils
class AuthServer:
    """
    Builds nested JSON per Auth Server with scopes, claims, policies, and rules.
    """

    def build(self, db):
        logger.info("Fetching collections for Auth Server nested builder...")

        # Check available collections
        collections = db.list_collection_names()
        logger.info(f"Available collections: {collections}")

        # Directly retrieve already formatted docs (without _id)
        authorization_server_list = list(db["okta_auth_server"].find({}, {"_id": 0}))
        scopes = list(db["okta_auth_server_scope"].find({}, {"_id": 0}))
        claims = list(db["okta_auth_server_claim"].find({}, {"_id": 0}))
        policies = list(db["okta_auth_server_policy"].find({}, {"_id": 0}))
        rules = list(db["okta_auth_server_policy_rule"].find({}, {"_id": 0}))
        trusted_Server = list(db["okta_trusted_server"].find({}, {"_id": 0}))

        logger.info(f"Found {len(authorization_server_list)} auth servers, {len(scopes)} scopes, {len(claims)} claims, {len(policies)} policies, {len(rules)} rules, {len(trusted_Server)} servers")

        results = []
        for server in authorization_server_list:
            server_id = server.get("name")
            logger.info(f"Building nested data for auth server: {server_id}")

            formatted = {
                **server,  # take all fields as already formatted in DB
                "authorization_server_scopes": [scope for scope in scopes if scope.get("auth_server_id") == server_id] or [],
                "authorization_server_claims": [claim for claim in claims if claim.get("auth_server_id") == server_id] or [],
                "authorization_server_accessPolicies": [policy for policy in policies if policy.get("auth_server_id") == server_id] or [],
                "authorization_server_accessPoliciesRules": [rule for rule in rules if rule.get("auth_server_id") == server_id] or [],
                "authorization_server_trusted_servers": [server for server in trusted_Server if server.get("auth_server_id") == server_id] or [],
            }

            logger.info(f"Auth server {server_id} has {len(formatted['authorization_server_scopes'])} scopes, {len(formatted['authorization_server_claims'])} claims, {len(formatted['authorization_server_accessPolicies'])} policies, {len(formatted['authorization_server_accessPoliciesRules'])} rules")
            results.append(formatted)

        logger.info(f" Built nested Auth Server data for {len(results)} servers")
        return {"auth_server_list": results}
