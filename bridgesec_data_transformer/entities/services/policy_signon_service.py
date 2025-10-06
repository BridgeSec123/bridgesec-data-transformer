from typing import Dict, Any, List, Optional
from pymongo import MongoClient
from django.conf import settings
from datetime import datetime, timedelta
import logging
import re

logger = logging.getLogger(__name__)

# Import utility functions from core.utils
from core.utils.db_utils import get_collection_name, get_latest_db


class PolicySignonDataBuilder:
    """
    Builds nested JSON per Policy Signon with policy signon password rules.
    """

    def __init__(self):
        # Define specific priorities for certain policy names
        self.custom_priorities = {
            "MFA Test": 1,
            "MSFT Global": 2,
            "Test Policy": 3,
            "cic": 4,
            "passwordless": 5,
            "usernamePasswordPolicy": 6,
            "xcvvfe": 7,
            "Default Policy": 10,
        }
        self.policy_priority_map = {}

    def assign_unique_priorities(self, policies):
        """Assign priorities: custom first, then sequential for remaining"""
        # Assign custom priorities
        self.policy_priority_map.update({
            policy.get("name"): priority
            for policy in policies
            for name, priority in self.custom_priorities.items()
            if policy.get("name") == name
        })

        # Assign sequential priorities to remaining policies
        used_priorities = set(self.custom_priorities.values())
        remaining_policies = [p for p in policies if p.get("name") not in self.policy_priority_map]

        next_priority = 1
        for policy in sorted(remaining_policies, key=lambda p: p.get("name", "")):
            if policy_name := policy.get("name"):
                while next_priority in used_priorities:
                    next_priority += 1
                self.policy_priority_map[policy_name] = next_priority
                used_priorities.add(next_priority)
                next_priority += 1

        logger.info(f"Priority assignments: {self.policy_priority_map}")

    def get_policy_priority(self, policy_name):
        """Get the assigned priority for a policy"""
        return self.policy_priority_map.get(policy_name, 999)

    def build(self, db):
        logger.info( f"Fetching collections for Policy Signon nested builder...")

        # Check available collections
        collections = db.list_collection_names()
        logger.info(f"Available collections: {collections}")

        # Directly retrieve already formatted docs (without _id)
        policies = list(db["okta_policy_sign_on"].find({}, {"_id": 0}))
        policy_rules = list(db["okta_policy_rule_sign_on"].find({}, {"_id": 0})) 

        logger.info(f"Found {len(policies)} Signon policies, {len(policy_rules)} policy signon password rules")

        # Assign unique priorities to all policies
        self.assign_unique_priorities(policies)

        results = []
        for policy in policies:
            policy_name = policy.get("name")
            priority = self.get_policy_priority(policy_name)

            # Debug: Log what we're assigning
            logger.info(f"Policy '{policy_name}' getting priority {priority}")

            # Get all rules for this policy
            matching_rules = [rule for rule in policy_rules if rule.get("policy_id") == policy_name]
            logger.info(f"Found {len(matching_rules)} rules for policy '{policy_name}'")

            # Sort rules by their original priority to maintain order
            matching_rules.sort(key=lambda r: r.get("priority", 999))

            # Reassign rule priorities starting from 1 (scoped within this policy)
            processed_rules = []
            for index, rule in enumerate(matching_rules, start=1):
                rule_name = rule.get("name", "")
                original_priority = rule.get("priority", "")
                logger.info(f"  Rule '{rule_name}' changing from priority {original_priority} to {index}")

                processed_rules.append({
                    **rule,
                    "priority": index  # Rule priorities start at 1 within each policy
                })

            result = {
                **policy,
                "priority": priority,
                "policy_signon_rules": processed_rules
            }
            results.append(result)

        logger.info(f"Built nested Policy Signon data for {len(results)} policies")
        return results