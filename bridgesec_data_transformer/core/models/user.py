from mongoengine import Document, StringField

class User(Document):
    username = StringField(required=True, unique=True)
    email = StringField(required=True, unique=True)
    password = StringField(required=True)
    role = StringField(default="user")

    meta = {
        "collection": "users",
        "alias": "bridgesec"
    }

    @property
    def is_authenticated(self):
        return True