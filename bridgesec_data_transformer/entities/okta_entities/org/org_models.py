from mongoengine import StringField

from entities.models.base import BaseEntityModel


class Org(BaseEntityModel):
    company_name = StringField()
    website = StringField(required=False, null=True)
    address1 = StringField(required=False, null=True)
    address2 = StringField(required=False, null=True)
    billing_contact_user = StringField(required=False, null=True)  
    city = StringField(required=False, null=True)
    country = StringField(required=False, null=True)
    end_user_support_help_url = StringField(required=False, null=True)
    logo = StringField(required=False, null=True)
    opt_out_communication_emails = StringField(required=False, null=True)
    phone_number = StringField(required=False, null=True)
    postal_code = StringField(required=False, null=True)
    state = StringField(required=False,  null=True)
    support_phone_number = StringField(required=False, null=True)
    technical_contact_user = StringField(required=False, null=True)
    
    meta = {"collection": "okta_org_configuration"}
