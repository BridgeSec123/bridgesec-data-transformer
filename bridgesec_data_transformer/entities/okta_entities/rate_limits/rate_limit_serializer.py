from rest_framework import serializers


class PrincipalRateLimitSerializer(serializers.Serializer):
    rate_limit_id = serializers.CharField(required=False, allow_blank=True)
    principal_id = serializers.CharField(max_length=255, required=True)
    principal_type = serializers.CharField(max_length=50, required=True)
    default_percentage = serializers.IntegerField(required=False)
    default_concurrency_percentage = serializers.IntegerField(required=False)
    created_by = serializers.CharField(required=False, allow_blank=True)
    created_date = serializers.CharField(required=False, allow_blank=True)
    last_update = serializers.CharField(required=False, allow_blank=True)
    last_updated_by = serializers.CharField(required=False, allow_blank=True)
    org_id = serializers.CharField(required=False, allow_blank=True)


class RateLimitAdminNotificationSerializer(serializers.Serializer):
    notification_id = serializers.CharField(required=False, allow_blank=True)
    notifications_enabled = serializers.CharField(max_length=50, required=False, allow_blank=True)

class RateLimitWarningThresholdSerializer(serializers.Serializer):
    threshold_id = serializers.CharField(required=False, allow_blank=True)
    warning_threshold = serializers.IntegerField(required=False)