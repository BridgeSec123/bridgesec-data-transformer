from mongoengine import IntField, StringField

from entities.models.base import BaseEntityModel


class PrincipalRateLimit(BaseEntityModel):
    principal_id = StringField(required=True)
    principal_type = StringField(required=True)

    meta = {"collection": "okta_principal_rate_limits"}


class RateLimitAdminNotification(BaseEntityModel):
    notifications_enabled = StringField(required=True)

    meta = {"collection": "okta_rate_limit_admin_notification"}

class RateLimitWarningThreshold(BaseEntityModel):
    warning_threshold = IntField(required=True)

    meta = {"collection": "okta_rate_limit_warning_threshold_percentage"}
