from datetime import datetime

from mongoengine import (BooleanField, DateTimeField, Document, StringField)


class Tenant(Document):
    """Represents one customer's isolated Okta + infrastructure configuration."""

    name = StringField(required=True, unique=True)
    okta_domain = StringField(required=True, unique=True)   # e.g. "acme.okta.com"
    okta_client_id = StringField(required=True)
    okta_client_secret = StringField(required=True)
    okta_issuer = StringField(required=True)

    # Per-tenant MongoDB storage
    mongo_uri = StringField(required=True)
    mongo_db_prefix = StringField(required=True)           # e.g. "acme_okta" → snapshots: "acme_okta_2026-03-20T1435"

    # Per-tenant Terraform / Supabase config
    terraform_server_url = StringField(required=True)
    terraform_state_path = StringField(required=True)      # Supabase path for this tenant's state file

    # Service app credentials (for scheduled bulk fetch)
    service_client_id = StringField()
    service_private_key = StringField()
    service_scopes = StringField()

    is_active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.utcnow)

    meta = {
        "collection": "tenants",
        "alias": "bridgesec",
    }
