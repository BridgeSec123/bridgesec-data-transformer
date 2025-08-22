from mongoengine import ListField, StringField

from entities.models.base import BaseEntityModel


class NetworkZone(BaseEntityModel):
    name = StringField(required=True)
    type = StringField(required=True)
    asns = ListField(required=False, null=True)
    dynamic_locations = ListField(required=False, null=True)
    dynamic_locations_excluded = ListField(required=False, null=True)
    dynamic_proxy_type = StringField(required=False, null=True)
    gateways = ListField(required=False, null=True)
    ip_service_categories_exclude = ListField(required=False, null=True)
    ip_service_categories_include = ListField(required=False, null=True)
    proxies = ListField(required=False, null=True)
    status = StringField(required=False, null=True)
    usage = StringField(required=False, null=True)
    
    meta = {"collection": "okta_network_zone"}