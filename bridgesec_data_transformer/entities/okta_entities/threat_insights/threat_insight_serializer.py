from rest_framework import serializers


class ThreatInsightSerializer(serializers.Serializer):
    action = serializers.CharField(required=True)
    network_excludes = serializers.ListField(required=False)