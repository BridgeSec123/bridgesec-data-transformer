from rest_framework import serializers


# Remediation Settings Serializer
class RemediationSettingsSerializer(serializers.Serializer):
    access_approved = serializers.CharField(max_length=100, required=True)
    access_revoked = serializers.CharField(max_length=100, required=True)
    no_response = serializers.CharField(max_length=100, required=True)


# Resource Settings Serializers
class ExcludedResourcesSerializer(serializers.Serializer):
    resource_id = serializers.CharField(max_length=255, required=False)
    resource_type = serializers.CharField(max_length=100, required=False)


class EntitlementValuesSerializer(serializers.Serializer):
    id = serializers.CharField(max_length=255, required=True)


class EntitlementsSerializer(serializers.Serializer):
    id = serializers.CharField(max_length=255, required=True)
    include_all_values = serializers.BooleanField(required=False)
    values = serializers.ListField(child=EntitlementValuesSerializer(), required=False)


class EntitlementBundlesSerializer(serializers.Serializer):
    id = serializers.CharField(max_length=255, required=True)


class TargetResourcesSerializer(serializers.Serializer):
    resource_id = serializers.CharField(max_length=255, required=True)
    resource_type = serializers.CharField(max_length=100, required=True)
    include_all_entitlements_and_bundles = serializers.BooleanField(required=False)
    entitlement_bundles = serializers.ListField(child=EntitlementBundlesSerializer(), required=False)
    entitlements = serializers.ListField(child=EntitlementsSerializer(), required=False)


class ResourceSettingsSerializer(serializers.Serializer):
    type = serializers.CharField(max_length=100, required=True)
    include_admin_roles = serializers.CharField(max_length=50, required=False)
    include_entitlements = serializers.BooleanField(required=False)
    individually_assigned_apps_only = serializers.BooleanField(required=False)
    individually_assigned_groups_only = serializers.BooleanField(required=False)
    only_include_out_of_policy_entitlements = serializers.BooleanField(required=False)
    excluded_resources = serializers.ListField(child=ExcludedResourcesSerializer(), required=False)
    target_resources = serializers.ListField(child=TargetResourcesSerializer(), required=False)


# Reviewer Settings Serializers
class StartReviewSerializer(serializers.Serializer):
    on_day = serializers.IntegerField(required=False)
    when = serializers.CharField(max_length=100, required=False)


class ReviewerLevelsSerializer(serializers.Serializer):
    type = serializers.CharField(max_length=100, required=True)
    fallback_reviewer_id = serializers.CharField(max_length=255, required=False)
    reviewer_group_id = serializers.CharField(max_length=255, required=False)
    reviewer_scope_expression = serializers.CharField(max_length=500, required=False)
    self_review_disabled = serializers.BooleanField(required=False)
    start_review = serializers.ListField(child=StartReviewSerializer(), required=False)


class ReviewerSettingsSerializer(serializers.Serializer):
    type = serializers.CharField(max_length=100, required=True)
    bulk_decision_disabled = serializers.BooleanField(required=False)
    fallback_reviewer_id = serializers.CharField(max_length=255, required=False)
    justification_required = serializers.BooleanField(required=False)
    reassignment_disabled = serializers.BooleanField(required=False)
    self_review_disabled = serializers.BooleanField(required=False)
    reviewer_group_id = serializers.CharField(max_length=255, required=False)
    reviewer_id = serializers.CharField(max_length=255, required=False)
    reviewer_scope_expression = serializers.CharField(max_length=500, required=False)
    reviewer_levels = serializers.ListField(child=ReviewerLevelsSerializer(), required=False)


# Schedule Settings Serializers
class RecurrenceSerializer(serializers.Serializer):
    interval = serializers.CharField(max_length=100, required=True)
    ends = serializers.CharField(max_length=100, required=False)
    repeat_on_type = serializers.CharField(max_length=100, required=False)


class ScheduleSettingsSerializer(serializers.Serializer):
    start_date = serializers.CharField(max_length=100, required=True)
    duration_in_days = serializers.IntegerField(required=True)
    time_zone = serializers.CharField(max_length=100, required=True)
    type = serializers.CharField(max_length=100, required=True)
    recurrence = serializers.ListField(child=RecurrenceSerializer(), required=False)


# Notification Settings Serializer
class NotificationSettingsSerializer(serializers.Serializer):
    notify_reviewer_at_campaign_end = serializers.BooleanField(required=True)
    notify_reviewer_during_midpoint_of_review = serializers.BooleanField(required=True)
    notify_reviewer_when_overdue = serializers.BooleanField(required=True)
    notify_reviewer_when_review_assigned = serializers.BooleanField(required=True)
    notify_review_period_end = serializers.BooleanField(required=True)
    reminders_reviewer_before_campaign_close_in_secs = serializers.ListField(child=serializers.IntegerField(), required=False)


# Principal Scope Settings Serializers
class PredefinedInactiveUsersScopeSerializer(serializers.Serializer):
    inactive_days = serializers.IntegerField(required=False)


class PrincipalScopeSettingsSerializer(serializers.Serializer):
    type = serializers.CharField(max_length=100, required=True)
    excluded_user_ids = serializers.ListField(child=serializers.CharField(), required=False)
    group_ids = serializers.ListField(child=serializers.CharField(), required=False)
    include_only_active_users = serializers.BooleanField(required=False)
    only_include_users_with_sod_conflicts = serializers.BooleanField(required=False)
    user_ids = serializers.ListField(child=serializers.CharField(), required=False)
    user_scope_expression = serializers.CharField(max_length=500, required=False)
    predefined_inactive_users_scope = serializers.ListField(child=PredefinedInactiveUsersScopeSerializer(), required=False)


# Campaign Serializer
class CampaignSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=True)
    remediation_settings = serializers.ListField(child=RemediationSettingsSerializer(), required=True)
    resource_settings = serializers.ListField(child=ResourceSettingsSerializer(), required=True)
    reviewer_settings = serializers.ListField(child=ReviewerSettingsSerializer(), required=True)
    schedule_settings = ScheduleSettingsSerializer(required=True)
    notification_settings = NotificationSettingsSerializer(required=True)
    campaign_tier = serializers.CharField(max_length=50, required=False)
    campaign_type = serializers.CharField(max_length=50, required=False, default="RESOURCE")
    description = serializers.CharField(max_length=1000, required=False)
    principal_scope_settings = serializers.ListField(child=PrincipalScopeSettingsSerializer(), required=False)
