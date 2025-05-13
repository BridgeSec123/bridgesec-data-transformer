from mongoengine import ListField, StringField

from entities.models.base import BaseEntityModel


class ThreatInsight(BaseEntityModel):
    action = StringField(required=True)
    network_excludes = ListField(required=False)
    
    meta = {"collection": "okta_threat_insight_settings"}