from rest_framework import serializers


class LogEntrySerializer(serializers.Serializer):
    """Represents a single log document from Elasticsearch."""
    id            = serializers.CharField(source="_id", read_only=True)
    timestamp     = serializers.CharField(allow_null=True)
    levelname     = serializers.CharField(allow_null=True)
    message       = serializers.CharField(allow_null=True)
    component     = serializers.CharField(allow_null=True)
    entity_type   = serializers.CharField(allow_null=True)
    request_id    = serializers.CharField(allow_null=True)
    user          = serializers.CharField(allow_null=True)
    tenant_id     = serializers.CharField(allow_null=True)
    operation     = serializers.CharField(allow_null=True)
    duration_ms   = serializers.FloatField(allow_null=True)
    resource_count= serializers.IntegerField(allow_null=True)
    hostname      = serializers.CharField(allow_null=True)
    environment   = serializers.CharField(allow_null=True)
    exc_info      = serializers.CharField(allow_null=True)


class LogQueryParamsSerializer(serializers.Serializer):
    """Validates and normalises query parameters for GET /api/logs/."""
    level       = serializers.ChoiceField(
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        required=False, allow_null=True
    )
    component   = serializers.CharField(required=False, allow_blank=True)
    entity_type = serializers.CharField(required=False, allow_blank=True)
    operation   = serializers.CharField(required=False, allow_blank=True)
    from_date   = serializers.DateTimeField(required=False, allow_null=True)
    to_date     = serializers.DateTimeField(required=False, allow_null=True)
    search      = serializers.CharField(required=False, allow_blank=True)
    page        = serializers.IntegerField(min_value=1, default=1)
    page_size   = serializers.IntegerField(min_value=1, max_value=500, default=50)
