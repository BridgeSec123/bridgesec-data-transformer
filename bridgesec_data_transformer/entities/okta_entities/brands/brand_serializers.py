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


class EmailDomainSerializer(serializers.Serializer):
    brand_id = serializers.CharField(max_length=255, required=True)
    display_name = serializers.CharField(max_length=255, required=True)
    domain = serializers.CharField(max_length=255, required=True)
    user_name = serializers.CharField(max_length=255, required=True)

class OktaThemeSerializer(serializers.Serializer): 
    brand_id = serializers.CharField(max_length=255, required=True)
    background_image = serializers.CharField(max_length=255, required=False)
    email_template_touch_point_variant = serializers.CharField(max_length=255, required=False)
    end_user_dashboard_touch_point_variant = serializers.CharField(max_length=255, required=False)
    error_page_touch_point_variant = serializers.CharField(max_length=255, required=False)
    favicon = serializers.CharField(max_length=255, required=False)
    logo = serializers.CharField(max_length=255, required=False)
    primary_color_contrast_hex = serializers.CharField(max_length=255, required=False)
    primary_color_hex = serializers.CharField(max_length=255, required=False)
    secondary_color_contrast_hex = serializers.CharField(max_length=255, required=False)
    secondary_color_hex = serializers.CharField(max_length=255, required=False)
    sign_in_page_touch_point_variant = serializers.CharField(max_length=255, required=False)
    theme_id = serializers.CharField(max_length=255, required=False)    