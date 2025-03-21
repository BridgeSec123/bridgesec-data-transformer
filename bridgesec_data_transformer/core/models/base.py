from datetime import datetime
from mongoengine import Document, StringField, DateTimeField, ListField, DictField


class BaseOktaModel(Document):
    _id = StringField(primary_key=True)
    created_at = DateTimeField(default=datetime.now)
    versions = ListField(DictField())
    
    meta = {'abstract': True}