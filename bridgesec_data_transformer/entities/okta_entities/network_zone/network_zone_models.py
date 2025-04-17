from mongoengine import ListField, StringField

from entities.models.base import BaseEntityModel


class NetworkZone(BaseEntityModel):
    name = StringField(required=True)
    type = StringField(required=True)
    asns = ListField(required=False)
    dynamic_locations = ListField(required=False)
    dynamic_locations_excluded = ListField(required=False)
    dynamic_proxy_type = StringField(required=False)
    gateways = ListField(required=False)
    ip_service_categories_exclude = ListField(required=False)
    ip_service_categories_include = ListField(required=False)
    proxies = ListField(required=False)
    status = StringField(required=False)
    usage = StringField(required=False)