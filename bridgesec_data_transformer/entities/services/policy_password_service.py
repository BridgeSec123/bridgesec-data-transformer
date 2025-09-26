from typing import Dict, Any, List, Optional
from pymongo import MongoClient
from django.conf import settings
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Import utility functions from core.utils
from core.utils.db_utils import get_collection_name, get_latest_db


class PolicyPasswordDataBuilder:
    """
    Builds nested JSON per Policy Password with policy password rules.
    """

    def build(self, db):
        logger.info("Fetching collections for Policy Password nested builder...")

        # Check available collections
        collections = db.list_collection_names()
        logger.info(f"Available collections: {collections}")

        # Directly retrieve already formatted docs (without _id)
        policies = list(db["okta_policy_password"].find({}, {"_id": 0}))
        policy_password_rules = list(db["okta_policy_rule_password"].find({}, {"_id": 0}))

        logger.info(f"Found {len(policies)} Password policies, {len(policy_password_rules)} policy password rules")

        results = []
        for policy in policies:
            policy_name = policy.get("name")
            logger.info(f"Building nested data for Password policy: {policy_name}")

            formatted = {
                **policy,  # take all fields as already formatted in DB
                "policy_password_rules": [rule for rule in policy_password_rules if rule.get("policy_id") == policy_name] or []
            }

            logger.info(f"Password policy {policy_name} has {len(formatted['policy_password_rules'])} policy password rules")
            results.append(formatted)

        logger.info(f"Built nested Policy Password data for {len(results)} policies")
        return {"policy_password_list": results}