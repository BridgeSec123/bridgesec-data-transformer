import logging

from entities.services.service_utils import fetch_collection

logger = logging.getLogger(__name__)


class PolicyEnrollmentDataBuilder:
    """
    Builds nested JSON per Policy Enrollment with policy enrollment rules.
    Fetches data directly from DB collections without merging.
    """

    def build(self, db):
        logger.info("Fetching Policy Enrollment data from DB...")

        # Fetch parent policies from DB
        policies = fetch_collection(db, "okta_policy_profile_enrollment")
        logger.info(f"Found {len(policies)} Enrollment policies")

        # Fetch policy rules from DB
        all_policy_rules = fetch_collection(db, "okta_policy_rule_profile_enrollment")

        # Fetch policy apps from DB
        all_policy_apps = fetch_collection(db, "okta_policy_profile_enrollment_apps")

        logger.info(f"Found {len(all_policy_rules)} Enrollment policy rules, {len(all_policy_apps)} policy apps")

        # Build nested structure
        results = []
        for policy in policies:
            policy_id = policy.get("policy_id") or policy.get("name")

            # Find all rules and apps for this policy
            policy_rules = [rule for rule in all_policy_rules if rule.get("policy_id") == policy_id]
            policy_apps = [app for app in all_policy_apps if app.get("policy_id") == policy_id]

            formatted = {
                **policy,  # Include all policy fields
                "policy_enrollment_rules": policy_rules,
                "policy_enrollment_apps": policy_apps,
            }

            logger.info(f"Enrollment policy {policy_id} has {len(policy_rules)} policy_enrollment_rules and {len(policy_apps)} policy_enrollment_apps")
            results.append(formatted)

        logger.info(f"Built nested Policy Enrollment data for {len(results)} policies")
        return results
