import logging

from entities.services.service_utils import fetch_collection

logger = logging.getLogger(__name__)


class PolicyMFADataBuilder:
    """
    Builds nested JSON per Policy MFA with policy rules.
    Fetches data directly from DB collections without merging.
    """

    def build(self, db):
        logger.info("Fetching Policy MFA data from DB...")

        # Fetch parent policies from DB
        policies = fetch_collection(db, "okta_policy_mfa")
        logger.info(f"Found {len(policies)} MFA policies")

        # Fetch policy rules from DB
        all_policy_rules = fetch_collection(db, "okta_policy_rule_mfa")
        logger.info(f"Found {len(all_policy_rules)} MFA policy rules")

        # Build nested structure
        results = []
        for policy in policies:
            policy_id = policy.get("policy_id") or policy.get("name")

            # Find all rules for this policy
            policy_rules = [rule for rule in all_policy_rules if rule.get("policy_id") == policy_id]

            formatted = {
                **policy,  # Include all policy fields
                "policy_rules": policy_rules,
            }

            logger.info(f"MFA policy {policy_id} has {len(policy_rules)} policy rules")
            results.append(formatted)

        logger.info(f"Built nested Policy MFA data for {len(results)} policies")
        return results
