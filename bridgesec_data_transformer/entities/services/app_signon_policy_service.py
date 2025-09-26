from typing import Dict, Any, List, Optional
from pymongo import MongoClient
from django.conf import settings
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Import utility functions from core.utils
from core.utils.db_utils import get_collection_name, get_latest_db
# Import entity filters
from entities.entity_filters import should_skip_app_signon_policy_extraction


class AppSignonPolicyDataBuilder:
    """
    Builds nested JSON per App Signon Policy with policy rules.
    """

    def build(self, db):
        logger.info("Fetching collections for App Signon Policy nested builder...")

        # Check available collections
        collections = db.list_collection_names()
        logger.info(f"Available collections: {collections}")

        # Directly retrieve already formatted docs (without _id)
        policies = list(db["okta_app_signon_policy"].find({}, {"_id": 0}))
        policy_rules = list(db["okta_app_signon_policy_rule"].find({}, {"_id": 0}))

        logger.info(f"Found {len(policies)} App Signon policies, {len(policy_rules)} policy rules")

        results = []
        for policy in policies:
            policy_name = policy.get("name")
            logger.info(f"Building nested data for App Signon policy: {policy_name}")

            formatted = {
                **policy,  # take all fields as already formatted in DB
                "policy_rules": [rule for rule in policy_rules if rule.get("policy_id") == policy_name],
            }

            logger.info(f"App Signon policy {policy_name} has {len(formatted['policy_rules'])} policy rules")
            results.append(formatted)

        logger.info(f"Built nested App Signon Policy data for {len(results)} policies")
        return {"app_signon_policy_list": results}