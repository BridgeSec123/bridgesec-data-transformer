from datetime import datetime

from mongoengine import (DateTimeField, DictField, Document, ObjectIdField,
                         StringField)


class ActivityLog(Document):
    """Per-tenant audit log for all significant user and system actions."""

    tenant_id = ObjectIdField(required=True)
    user_email = StringField()
    action = StringField()       # login | logout | bulk_fetch | restore | create | delete | view
    entity_name = StringField()
    db_name = StringField()      # which snapshot DB was touched
    details = DictField()        # operation count, record IDs, errors, etc.
    status = StringField()       # success | error | partial_success
    ip_address = StringField()
    timestamp = DateTimeField(default=datetime.utcnow)

    meta = {
        "collection": "activity_logs",
        "alias": "bridgesec",
        "indexes": [
            "tenant_id",
            ("tenant_id", "-timestamp"),
            "action",
        ],
    }
