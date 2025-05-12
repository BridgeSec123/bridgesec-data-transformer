from rest_framework import serializers

class CaptchaSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    type = serializers.CharField(max_length=255)
    site_key = serializers.CharField(max_length=255)
    string_key = serializers.CharField(max_length=255)

class CaptchaOrgWideSettingsSerializer(serializers.Serializer):
    captcha_id = serializers.CharField(max_length=255)
    enabled_for = serializers.ListField(child=serializers.CharField(max_length=255))