from mongoengine import StringField

from entities.models.base import BaseEntityModel


class Org(BaseEntityModel):
    company_name = StringField()
    website = StringField(required=False)
    address1 = StringField(required=False)
    address2 = StringField(required=False)
    billing_contact_user = StringField(required=False)  
    city = StringField(required=False)
    country = StringField(required=False)
    end_user_support_help_url = StringField(required=False)
    logo = StringField(required=False)
    opt_out_communication_emails = StringField(required=False)
    phone_number = StringField(required=False)
    postal_code = StringField(required=False)
    state = StringField(required=False)
    support_phone_number = StringField(required=False)
    technical_contact_user = StringField(required=False)
    
    meta = {"collection": "okta_org_configuration"}
