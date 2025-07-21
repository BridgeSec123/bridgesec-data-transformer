from mongoengine import Document, StringField

class User(Document):
    ROLE_CHOICES = ['admin', 'user'] 

    username = StringField(required=True)
    email = StringField(required=True, unique=True)
    password = StringField(required=False)
    role = StringField(max_length=10, choices=ROLE_CHOICES, default='user')

    meta = {
        "collection": "users",
        "alias": "bridgesec"
    }
 
    @property
    def is_authenticated(self):
        return True