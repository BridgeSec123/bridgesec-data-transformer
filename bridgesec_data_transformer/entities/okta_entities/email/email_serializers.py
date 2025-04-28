from rest_framework import serializers


class EmailCustomizationSerializer(serializers.Serializer):
    brand_id = serializers.CharField(max_length=255, required=False)
    template_name = serializers.CharField(max_length=255, required=False)
    body = serializers.CharField(required=False)
    force_is_default = serializers.BooleanField(required=False)
    is_default = serializers.BooleanField(required=False)
    language = serializers.CharField(max_length=255, required=False)
    subject = serializers.CharField(max_length=255, required=False)

class EmailTemplateSettingsSerializer(serializers.Serializer):
    brand_id = serializers.CharField(max_length=255, required=False)
    template_name = serializers.CharField(max_length=255, required=False)
    recipients = serializers.CharField(max_length=255, required=False)

class EmailSecurityNotificationSerializer(serializers.Serializer):
    report_suspicious_activity_enabled = serializers.BooleanField(required=False)
    send_email_for_factor_enrollment_enabled = serializers.BooleanField(required=False)
    send_email_for_factor_reset_enabled = serializers.BooleanField(required=False)
    send_email_for_new_device_enabled = serializers.BooleanField(required=False)
    send_email_for_password_changed_enabled = serializers.BooleanField(required=False)