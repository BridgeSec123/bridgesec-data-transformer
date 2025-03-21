from mongoengine import DictField, StringField
from core.models.base import BaseOktaModel


class Group(BaseOktaModel):
    name = StringField()
    description = StringField()
    custom_profile_attributes = DictField(required=False)
    data = DictField()

    meta = {"collection": "groups"}
