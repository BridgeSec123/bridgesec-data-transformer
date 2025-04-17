from rest_framework import serializers


class BrandSerializer(serializers.Serializer):
    name = serializers.CharField()
    agree_to_custom_privacy_policy = serializers.BooleanField(required=False)
    brand_id = serializers.CharField(required=False)
    custom_privacy_policy_url = serializers.CharField(required=False)
    default_app_app_instance_id = serializers.CharField(required=False)
    default_app_app_link_name = serializers.CharField(required=False)
    default_app_classic_application_uri = serializers.CharField(required=False)
    locale = serializers.CharField(required=False)
    remove_powered_by_okta = serializers.BooleanField(required=False)
