from mongoengine import DictField
from core.models.base import BaseOktaModel


class UserProfile(BaseOktaModel):
    data = DictField()

    meta = {"collection": "users"}
