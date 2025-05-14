from mongoengine import DictField, ListField, StringField

from entities.models.base import BaseEntityModel


class EventHook(BaseEntityModel):
    name = StringField(required=True)
    events = ListField(required=True)
    channel = DictField(required=True)
    auth = DictField(null = True, required=False)
    
    meta = {"collection": "okta_event_hook"}