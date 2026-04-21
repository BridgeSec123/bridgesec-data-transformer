from mongoengine import IntField, StringField

from entities.models.base import BaseEntityModel


class PrincipalRateLimit(BaseEntityModel):
    rate_limit_id = StringField(required=False)
    principal_id = StringField(required=True)
    principal_type = StringField(required=True)
    default_percentage = IntField(required=False)
    default_concurrency_percentage = IntField(required=False)
    created_by = StringField(required=False)
    created_date = StringField(required=False)
    last_update = StringField(required=False)
    last_updated_by = StringField(required=False)
    org_id = StringField(required=False)

    meta = {"collection": "okta_principal_rate_limits"}


class RateLimitAdminNotification(BaseEntityModel):
    notification_id = StringField(required=False)
    notifications_enabled = StringField(required=False)

    meta = {"collection": "okta_rate_limit_admin_notification"}

class RateLimitWarningThreshold(BaseEntityModel):
    threshold_id = StringField(required=False)
    warning_threshold = IntField(required=False)

    meta = {"collection": "okta_rate_limit_warning_threshold_percentage"}
