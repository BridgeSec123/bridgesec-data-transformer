import logging
from typing import Any, Dict, List, Optional

from entities.services.service_utils import fetch_collection

logger = logging.getLogger(__name__)


class AppSignonPolicyDataBuilder:
    """
    Builds nested JSON per App Signon Policy with policy rules.
    Fetches data directly from DB collections without merging.
    """

    def build(self, db):
        logger.info("Fetching App Signon Policy data from DB...")

        # Fetch parent policies from DB
        policies = fetch_collection(db, "okta_app_signon_policy")
        logger.info(f"Found {len(policies)} App Signon policies")

        # Fetch policy rules from DB
        all_policy_rules = fetch_collection(db, "okta_app_signon_policy_rule")
        logger.info(f"Found {len(all_policy_rules)} App Signon policy rules")

        # Build nested structure
        results = []
        for policy in policies:
            policy_id = policy.get("app_policy_id")

            # Find all rules for this policy
            policy_rules = [rule for rule in all_policy_rules if rule.get("policy_id") == policy_id]

            formatted = {
                **policy,  # Include all policy fields
                "policy_rules": policy_rules,
            }

            logger.info(f"App Signon policy {policy_id} has {len(policy_rules)} policy rules")
            results.append(formatted)

        logger.info(f"Built nested App Signon Policy data for {len(results)} policies")
        return results