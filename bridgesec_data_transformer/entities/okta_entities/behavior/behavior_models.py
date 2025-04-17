from mongoengine import IntField, StringField

from entities.models.base import BaseEntityModel


class Behavior(BaseEntityModel):
    name = StringField(required=True)
    type = StringField(required=True)
    location_granularity_type = StringField(required=False)
    number_of_authentications = IntField(required=False)
    radius_from_location = IntField(required=False)
    status = StringField(required=False)
    velocity = IntField(required=False)
    
    meta = {"collection": "behavior"}