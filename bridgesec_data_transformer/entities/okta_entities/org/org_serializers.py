from rest_framework import serializers


class OrgSerializer(serializers.Serializer):
    company_name = serializers.CharField()
    website = serializers.CharField(required=False)
    address_1 = serializers.CharField(required=False)
    address_2 = serializers.CharField(required=False)
    billing_contact_user = serializers.CharField(required=False)
    city = serializers.CharField(required=False)
    country = serializers.CharField(required=False)
    end_user_support_help_url = serializers.CharField(required=False)
    logo = serializers.CharField(required=False)
    opt_out_communication_emails = serializers.CharField(required=False)
    phone_number = serializers.CharField(required=False)
    postal_code = serializers.CharField(required=False)
    state = serializers.CharField(required=False)
    support_phone_number = serializers.CharField(required=False)
    technical_contact_user = serializers.CharField(required=False)
