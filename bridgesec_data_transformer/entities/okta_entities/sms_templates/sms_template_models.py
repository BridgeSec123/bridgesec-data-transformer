from mongoengine import EmbeddedDocument, EmbeddedDocumentListField, StringField

from entities.models.base import BaseEntityModel


class Translation(EmbeddedDocument):
    language = StringField(required=True)
    template = StringField(required=True)

class SmsTemplate(BaseEntityModel):
    type = StringField(required=True)
    template = StringField(required=True)
    translations = EmbeddedDocumentListField(Translation)

    meta = {"collection": "okta_template_sms"}