from mongoengine import StringField, ListField, DictField, BooleanField, IntField, EmbeddedDocument, EmbeddedDocumentField, EmbeddedDocumentListField

from entities.models.base import BaseEntityModel


# Remediation Settings
class RemediationSettings(EmbeddedDocument):
    access_approved = StringField(required=True)
    access_revoked = StringField(required=True)
    no_response = StringField(required=True)


# Resource Settings and nested schemas
class ExcludedResources(EmbeddedDocument):
    resource_id = StringField(required=False)
    resource_type = StringField(required=False)


class EntitlementValues(EmbeddedDocument):
    id = StringField(required=True)


class Entitlements(EmbeddedDocument):
    id = StringField(required=True)
    include_all_values = BooleanField(required=False)
    values = EmbeddedDocumentListField(EntitlementValues, required=False)


class EntitlementBundles(EmbeddedDocument):
    id = StringField(required=True)


class TargetResources(EmbeddedDocument):
    resource_id = StringField(required=True)
    resource_type = StringField(required=True)
    include_all_entitlements_and_bundles = BooleanField(required=False)
    entitlement_bundles = EmbeddedDocumentListField(EntitlementBundles, required=False)
    entitlements = EmbeddedDocumentListField(Entitlements, required=False)


class ResourceSettings(EmbeddedDocument):
    type = StringField(required=True)
    include_admin_roles = StringField(required=False)
    include_entitlements = BooleanField(required=False)
    individually_assigned_apps_only = BooleanField(required=False)
    individually_assigned_groups_only = BooleanField(required=False)
    only_include_out_of_policy_entitlements = BooleanField(required=False)
    excluded_resources = EmbeddedDocumentListField(ExcludedResources, required=False)
    target_resources = EmbeddedDocumentListField(TargetResources, required=False)


# Reviewer Settings and nested schemas
class StartReview(EmbeddedDocument):
    on_day = IntField(required=False)
    when = StringField(required=False)


class ReviewerLevels(EmbeddedDocument):
    type = StringField(required=True)
    fallback_reviewer_id = StringField(required=False)
    reviewer_group_id = StringField(required=False)
    reviewer_scope_expression = StringField(required=False)
    self_review_disabled = BooleanField(required=False)
    start_review = EmbeddedDocumentListField(StartReview, required=False)


class ReviewerSettings(EmbeddedDocument):
    type = StringField(required=True)
    bulk_decision_disabled = BooleanField(required=False)
    fallback_reviewer_id = StringField(required=False)
    justification_required = BooleanField(required=False)
    reassignment_disabled = BooleanField(required=False)
    self_review_disabled = BooleanField(required=False)
    reviewer_group_id = StringField(required=False)
    reviewer_id = StringField(required=False)
    reviewer_scope_expression = StringField(required=False)
    reviewer_levels = EmbeddedDocumentListField(ReviewerLevels, required=False)


# Schedule Settings and nested schemas
class Recurrence(EmbeddedDocument):
    interval = StringField(required=True)
    ends = StringField(required=False)
    repeat_on_type = StringField(required=False)


class ScheduleSettings(EmbeddedDocument):
    start_date = StringField(required=True)
    duration_in_days = IntField(required=True)
    time_zone = StringField(required=True)
    type = StringField(required=True)
    recurrence = EmbeddedDocumentListField(Recurrence, required=False)


# Notification Settings
class NotificationSettings(EmbeddedDocument):
    notify_reviewer_at_campaign_end = BooleanField(required=True)
    notify_reviewer_during_midpoint_of_review = BooleanField(required=True)
    notify_reviewer_when_overdue = BooleanField(required=True)
    notify_reviewer_when_review_assigned = BooleanField(required=True)
    notify_review_period_end = BooleanField(required=True)
    reminders_reviewer_before_campaign_close_in_secs = ListField(IntField(), required=False)


# Principal Scope Settings and nested schemas
class PredefinedInactiveUsersScope(EmbeddedDocument):
    inactive_days = IntField(required=False)


class PrincipalScopeSettings(EmbeddedDocument):
    type = StringField(required=True)
    excluded_user_ids = ListField(StringField(), required=False)
    group_ids = ListField(StringField(), required=False)
    include_only_active_users = BooleanField(required=False)
    only_include_users_with_sod_conflicts = BooleanField(required=False)
    user_ids = ListField(StringField(), required=False)
    user_scope_expression = StringField(required=False)
    predefined_inactive_users_scope = EmbeddedDocumentListField(PredefinedInactiveUsersScope, required=False)


class Campaign(BaseEntityModel):
    name = StringField(required=True)
    remediation_settings = EmbeddedDocumentListField(RemediationSettings, required=True)
    resource_settings = EmbeddedDocumentListField(ResourceSettings, required=True)
    reviewer_settings = EmbeddedDocumentListField(ReviewerSettings, required=True)
    schedule_settings = EmbeddedDocumentField(ScheduleSettings, required=True)
    notification_settings = EmbeddedDocumentField(NotificationSettings, required=True)
    campaign_tier = StringField(required=False)
    campaign_type = StringField(required=False, default="RESOURCE")
    description = StringField(required=False)
    principal_scope_settings = EmbeddedDocumentListField(PrincipalScopeSettings, required=False)

    meta = {"collection": "okta_campaigns"}
