from typing import Dict, Any, List, Optional
from pymongo import MongoClient
from django.conf import settings
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Import utility functions from core.utils
from core.utils.db_utils import get_collection_name, get_latest_db


class PolicyMFADataBuilder:
    """
    Builds nested JSON per Policy MFA with policy rules.
    """

    def build(self, db):
        logger.info("Fetching collections for Policy MFA nested builder...")

        # Check available collections
        collections = db.list_collection_names()
        logger.info(f"Available collections: {collections}")

        # Directly retrieve already formatted docs (without _id)
        policies = list(db["okta_policy_mfa"].find({}, {"_id": 0}))
        policy_rules = list(db["okta_policy_rule_mfa"].find({}, {"_id": 0}))

        logger.info(f"Found {len(policies)} MFA policies, {len(policy_rules)} policy rules")

        results = []
        for policy in policies:
            policy_name = policy.get("name")
            logger.info(f"Building nested data for MFA policy: {policy_name}")

            formatted = {
                **policy,  # take all fields as already formatted in DB
                "policy_rules": [rule for rule in policy_rules if rule.get("policy_id") == policy_name] or [],
            }

            logger.info(f"MFA policy {policy_name} has {len(formatted['policy_rules'])} policy rules")
            results.append(formatted)

        logger.info(f"Built nested Policy MFA data for {len(results)} policies")
        return results