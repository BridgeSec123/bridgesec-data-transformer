from rest_framework import serializers


class BehaviorSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    type = serializers.CharField(max_length=255)
    location_granularity_type = serializers.CharField(max_length=255, required=False)
    number_of_authentications = serializers.IntegerField(required=False)
    radius_from_location = serializers.IntegerField(required=False)
    status = serializers.CharField(max_length=255, required=False)
    velocity = serializers.IntegerField(required=False)