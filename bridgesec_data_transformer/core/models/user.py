import logging
from bson import ObjectId
from mongoengine import Document, ObjectIdField, StringField

logger = logging.getLogger(__name__)


class User(Document):
    ROLE_CHOICES = ['admin', 'user']

    username = StringField(required=True)
    email = StringField(required=True, unique=True)
    password = StringField(required=False)
    role = StringField(max_length=10, choices=ROLE_CHOICES, default='user')
    tenant_id = ObjectIdField(required=False)  # None = super-admin (no tenant)

    meta = {
        "collection": "users",
        "alias": "bridgesec"
    }

    @property
    def is_authenticated(self):
        return True

    # ------------------------------------------------------------------
    # Shared interface methods — mirrors SupabaseUser so both backends
    # are interchangeable via _get_user_backend()
    # ------------------------------------------------------------------

    @classmethod
    def get_by_email(cls, email: str):
        """Return User for the given email, or None."""
        try:
            return cls.objects(email=email).first()
        except Exception as e:
            logger.error(f"User.get_by_email({email}) failed: {e}")
            return None

    @classmethod
    def get_by_id(cls, user_id: str):
        """Return User for the given id, or None."""
        try:
            return cls.objects.get(id=ObjectId(str(user_id)))
        except Exception as e:
            logger.error(f"User.get_by_id({user_id}) failed: {e}")
            return None

    @classmethod
    def create_or_update(cls, email: str, username: str, role: str = "user", tenant_id=None):
        """Find or create a user by email. Returns the User instance."""
        try:
            user = cls.objects(email=email).first()
            if user:
                if tenant_id and str(getattr(user, 'tenant_id', None)) != str(tenant_id):
                    user.tenant_id = ObjectId(str(tenant_id)) if tenant_id else None
                    user.save()
                return user
            user = cls(
                email=email,
                username=username or email,
                role=role,
                tenant_id=ObjectId(str(tenant_id)) if tenant_id else None,
            )
            user.save()
            return user
        except Exception as e:
            logger.error(f"User.create_or_update({email}) failed: {e}")
            raise

    @classmethod
    def list_all(cls, page: int = 1, page_size: int = 20):
        """Return a paginated list of users and total count."""
        try:
            offset = (page - 1) * page_size
            users = list(cls.objects.skip(offset).limit(page_size))
            total = cls.objects.count()
            return users, total
        except Exception as e:
            logger.error(f"User.list_all() failed: {e}")
            return [], 0

    @classmethod
    def delete_by_id(cls, user_id: str) -> bool:
        """Delete a user by id. Returns True if deleted, False if not found."""
        try:
            user = cls.get_by_id(user_id)
            if not user:
                return False
            user.delete()
            return True
        except Exception as e:
            logger.error(f"User.delete_by_id({user_id}) failed: {e}")
            return False