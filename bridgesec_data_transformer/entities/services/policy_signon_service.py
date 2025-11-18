import logging

from entities.services.service_utils import fetch_collection

logger = logging.getLogger(__name__)


class PolicySignonDataBuilder:
    """
    Builds nested JSON per Policy Signon with policy signon rules.
    Fetches data directly from DB collections without merging.
    Sorts policies and rules by existing priorities (ascending).
    """

    def build(self, db):
        logger.info("Fetching Policy Signon data from DB...")

        # Fetch parent policies from DB
        policies = fetch_collection(db, "okta_policy_sign_on")
        logger.info(f"Found {len(policies)} Signon policies")

        # Fetch policy rules from DB
        all_policy_rules = fetch_collection(db, "okta_policy_rule_sign_on")
        logger.info(f"Found {len(all_policy_rules)} Signon policy rules")

        # Build nested structure
        results = []
        for policy in policies:
            policy_id = policy.get("policy_signon_id") or policy.get("name")

            # Find all rules for this policy
            policy_rules = [rule for rule in all_policy_rules if rule.get("policy_id") == policy_id]

            # Sort rules by priority (ascending)
            policy_rules.sort(key=lambda r: r.get("priority", 999))

            formatted = {
                **policy,  # Include all policy fields
                "policy_signon_rules": policy_rules,
            }

            logger.info(f"Signon policy {policy_id} has {len(policy_rules)} policy signon rules")
            results.append(formatted)

        # Sort policies by priority (ascending)
        results.sort(key=lambda p: p.get("priority", 999))

        logger.info(f"Built nested Policy Signon data for {len(results)} policies")
        return results
