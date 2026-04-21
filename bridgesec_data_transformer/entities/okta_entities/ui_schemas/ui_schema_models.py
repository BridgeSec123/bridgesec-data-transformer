from entities.models.base import BaseEntityModel
from mongoengine import DictField, StringField


class UiSchema(BaseEntityModel):
    ui_schema_id = StringField(required=True)
    created = StringField(required=False)
    last_updated = StringField(required=False)
    ui_schema = DictField(required=False)

    meta = {"collection": "okta_ui_schema"}
