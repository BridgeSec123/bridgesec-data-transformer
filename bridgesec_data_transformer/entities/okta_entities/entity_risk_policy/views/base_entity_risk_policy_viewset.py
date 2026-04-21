import logging

from entities.views.base_view import BaseEntityViewSet

logger = logging.getLogger(__name__)


class BaseEntityRiskPolicyViewSet(BaseEntityViewSet):
    """
    Orchestrates fetch and store for entity risk policy and its rules.
    The entity risk policy is auto-created when ITP is enabled (singleton).
    """

    def fetch_and_store_data(self, db_name, request=None):
        from entities.okta_entities.entity_risk_policy.views.entity_risk_policy_viewset import EntityRiskPolicyViewSet
        from entities.okta_entities.entity_risk_policy.views.entity_risk_policy_rule_viewset import EntityRiskPolicyRuleViewSet

        policy_viewset = EntityRiskPolicyViewSet()
        data, status_code, _ = policy_viewset.fetch_from_okta(request=request)
        policies = policy_viewset.extract_data(data) if status_code == 200 else []
        policy_viewset.store_data(policies, db_name)

        rule_viewset = EntityRiskPolicyRuleViewSet()
        all_rules = []
        for policy in policies:
            policy_id = policy.get("policy_id")
            if not policy_id:
                continue
            rule_data = rule_viewset.fetch_from_okta(policy_id=policy_id, request=request)
            rules = rule_viewset.extract_data(rule_data, policy_id)
            all_rules.extend(rules)
        rule_viewset.store_data(all_rules, db_name)

        return {
            "okta_entity_risk_policy": policies,
            "okta_entity_risk_policy_rule": all_rules,
        }
