from mongoengine import ListField, StringField

from entities.models.base import BaseEntityModel


class OktaLinkDefinition(BaseEntityModel):
   associated_description = StringField(required=True)
   associated_name = StringField(required=True)
   associated_title = StringField(required=True)
   primary_description = StringField(required=True)
   primary_name = StringField(required=True)
   primary_title = StringField(required=True)

   meta = {'collection': 'okta_link_definition'}
