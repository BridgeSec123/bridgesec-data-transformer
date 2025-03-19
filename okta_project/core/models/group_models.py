from mongoengine import DictField
from core.models.base import BaseOktaModel


class Group(BaseOktaModel):
    data = DictField()

    meta = {"collection": "groups"}
