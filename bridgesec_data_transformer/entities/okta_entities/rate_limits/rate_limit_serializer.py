from rest_framework import serializers


class PrincipalRateLimitSerializer(serializers.Serializer):
    principal_id = serializers.CharField(max_length=255, required=True)
    principal_type = serializers.CharField(max_length=50, required=True)


class RateLimitAdminNotificationSerializer(serializers.Serializer):
    notifications_enabled = serializers.CharField(max_length=50, required=True)

class RateLimitWarningThresholdSerializer(serializers.Serializer):
    warning_threshold = serializers.IntegerField(required=True)