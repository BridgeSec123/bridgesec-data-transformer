from mongoengine import IntField, StringField

from entities.models.base import BaseEntityModel


class Behavior(BaseEntityModel):
    name = StringField(required=True)
    type = StringField(required=True)
    location_granularity_type = StringField(required=False, null=True)
    number_of_authentications = IntField(required=False, null=True)
    radius_from_location = IntField(required=False, null=True)
    status = StringField(required=False, null=True)
    velocity = IntField(required=False, null=True)
    
    meta = {"collection": "okta_behavior"}