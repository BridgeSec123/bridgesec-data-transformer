from rest_framework import serializers


class EntityRiskPolicySerializer(serializers.Serializer):
    policy_id = serializers.CharField(required=True)
    name = serializers.CharField(required=False, allow_blank=True)
    status = serializers.CharField(required=False, allow_blank=True)


class EntityRiskPolicyRuleSerializer(serializers.Serializer):
    policy_rule_id = serializers.CharField(required=True)
    policy_id = serializers.CharField(required=True)
    name = serializers.CharField(required=True)
    risk_level = serializers.CharField(required=False, allow_blank=True)
    status = serializers.CharField(required=False, allow_blank=True)
    priority = serializers.IntegerField(required=False, allow_null=True)
    users_included = serializers.ListField(child=serializers.CharField(), required=False)
    users_excluded = serializers.ListField(child=serializers.CharField(), required=False)
    groups_included = serializers.ListField(child=serializers.CharField(), required=False)
    groups_excluded = serializers.ListField(child=serializers.CharField(), required=False)
    terminate_all_sessions = serializers.BooleanField(required=False, allow_null=True)
    workflow_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
