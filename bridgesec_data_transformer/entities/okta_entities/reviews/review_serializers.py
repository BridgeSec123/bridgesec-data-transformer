from rest_framework import serializers


class ReviewSerializer(serializers.Serializer):
    review_id = serializers.CharField(required=True)
    campaign_id = serializers.CharField(required=False, allow_blank=True)
    resource_id = serializers.CharField(required=False, allow_blank=True)
    reviewer_id = serializers.CharField(required=False, allow_blank=True)
    reviewer_level = serializers.CharField(required=False, allow_blank=True)
    review_ids = serializers.ListField(child=serializers.CharField(), required=False)
    note = serializers.CharField(required=False, allow_blank=True)
    decision = serializers.CharField(required=False, allow_blank=True)
    reviewer_type = serializers.CharField(required=False, allow_blank=True)
    current_reviewer_level = serializers.CharField(required=False, allow_blank=True)
    created = serializers.CharField(required=False, allow_blank=True)
    created_by = serializers.CharField(required=False, allow_blank=True)
    last_updated = serializers.CharField(required=False, allow_blank=True)
    last_updated_by = serializers.CharField(required=False, allow_blank=True)
    decided = serializers.CharField(required=False, allow_blank=True)
    remediation_status = serializers.CharField(required=False, allow_blank=True)
    principal_profile = serializers.DictField(required=False)
