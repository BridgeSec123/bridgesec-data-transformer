from datetime import datetime
from mongoengine import Document, StringField, DateTimeField


class BaseOktaModel(Document):
    _id = StringField(primary_key=True)
    created_at = DateTimeField(default=datetime.now)
    
    meta = {'abstract': True}