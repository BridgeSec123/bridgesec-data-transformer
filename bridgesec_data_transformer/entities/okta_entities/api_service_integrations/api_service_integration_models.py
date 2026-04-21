from entities.models.base import BaseEntityModel
from mongoengine import ListField, StringField


class ApiServiceIntegration(BaseEntityModel):
    api_service_integration_id = StringField(required=True)
    type = StringField(required=True)
    name = StringField(required=False)
    config_guide_url = StringField(required=False)
    created = StringField(required=False)
    created_at = StringField(required=False)
    granted_scopes = ListField(StringField(), required=False)

    meta = {"collection": "okta_api_service_integration"}
