from mongoengine import StringField, ListField, DictField

from entities.models.base import BaseEntityModel


class Domain(BaseEntityModel):
    domain_id = StringField(required=True)
    name = StringField(required=False)
    brand_id = StringField(required=False)
    certificate_source_type = StringField(required=False)
    validation_status = StringField(required=False)
    dns_records = ListField(DictField(), required=False)
    public_certificate = DictField(required=False)

    meta = {"collection": "okta_domain"}
