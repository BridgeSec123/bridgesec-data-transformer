from bson import ObjectId
from mongoengine import Document, StringField


#Base class for all entity models
class BaseEntityModel(Document):
    _id = StringField(primary_key=True, default=lambda: str(ObjectId()))
    
    meta = {'db_alias': 'default', 'abstract': True}