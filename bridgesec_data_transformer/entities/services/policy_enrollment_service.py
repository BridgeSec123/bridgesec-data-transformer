from typing import Dict, Any, List, Optional
from pymongo import MongoClient
from django.conf import settings
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Import utility functions from core.utils
from core.utils.db_utils import get_collection_name, get_latest_db


class PolicyEnrollmentDataBuilder:
    """
    Builds nested JSON per Policy Enrollment with policy enrollment rules.
    """

    def build(self, db):
        logger.info(" Fetching collections for Policy Enrollment nested builder...")

        # Check available collections
        collections = db.list_collection_names()
        logger.info(f"Available collections: {collections}")

        # Directly retrieve already formatted docs (without _id)
        policies = list(db["okta_policy_profile_enrollment"].find({}, {"_id": 0}))
        policy_rules = list(db["okta_policy_rule_profile_enrollment"].find({}, {"_id": 0}))
        policy_rules_app = list(db["okta_policy_profile_enrollment_apps"].find({}, {"_id": 0}))

        logger.info(f"Found {len(policies)} Enrollment policies, {len(policy_rules)} policy enrollment rules")

        results = []
        for policy in policies:
            policy_name = policy.get("name")
            logger.info(f"Building nested data for Enrollment policy: {policy_name}")

            formatted = {
                **policy,  # take all fields as already formatted in DB
                "policy_enrollment_rules": [rule for rule in policy_rules if rule.get("policy_id") == policy_name] or [],
                "policy_enrollment_rules_app" : [rule for rule in policy_rules_app if rule.get("policy_id") == policy_name ] or [],
            }

            logger.info(f"Enrollment policy {policy_name} has {len(formatted['policy_enrollment_rules'])} policy_enrollment_rules")
            results.append(formatted)

        logger.info(f"Built nested Policy Enrollment data for {len(results)} policies")
        return {"policy_enrollment_list": results}