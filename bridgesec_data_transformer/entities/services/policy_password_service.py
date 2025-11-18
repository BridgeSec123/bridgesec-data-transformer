import logging

from entities.services.service_utils import fetch_collection

logger = logging.getLogger(__name__)


class PolicyPasswordDataBuilder:
    """
    Builds nested JSON per Policy Password with policy password rules.
    Fetches data directly from DB collections without merging.
    """

    def build(self, db):
        logger.info("Fetching Policy Password data from DB...")

        # Fetch parent policies from DB
        policies = fetch_collection(db, "okta_policy_password")
        logger.info(f"Found {len(policies)} Password policies")

        # Fetch policy rules from DB
        all_policy_rules = fetch_collection(db, "okta_policy_rule_password")
        logger.info(f"Found {len(all_policy_rules)} Password policy rules")

        # Build nested structure
        results = []
        for policy in policies:
            policy_id = policy.get("policy_id") or policy.get("name")

            # Find all rules for this policy
            policy_rules = [rule for rule in all_policy_rules if rule.get("policy_id") == policy_id]

            formatted = {
                **policy,  # Include all policy fields
                "policy_password_rules": policy_rules,
            }

            logger.info(f"Password policy {policy_id} has {len(policy_rules)} policy password rules")
            results.append(formatted)

        logger.info(f"Built nested Policy Password data for {len(results)} policies")
        return results
