from mongoengine import DictField, EmailField, StringField
from core.models.base import BaseOktaModel


class UserProfile(BaseOktaModel):
    firstName = StringField()
    lastName = StringField()
    mobilePhone = StringField(allow_null=True, required=False)
    secondEmail = StringField(allow_null=True, required=False)
    login = StringField()
    email = EmailField(unique=True)
    data = DictField()

    meta = {"collection": "users"}
