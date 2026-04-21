from django.conf import settings
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Import utility functions from core.utils
from core.utils.db_utils import get_collection_name, get_latest_db
from core.utils.collection_mapping import ENTITY_ID_MAPPING
from .auth_server_service import AuthServer
from .policy_mfa_service import PolicyMFADataBuilder
from .app_signon_policy_service import AppSignonPolicyDataBuilder
from .policy_password_service import PolicyPasswordDataBuilder
from .policy_enrollment_service import PolicyEnrollmentDataBuilder
from .policy_signon_service import PolicySignonDataBuilder
from .admin_role_custom_service import AdminRoleCustomDataBuilder


class EntityDataService:
    def __init__(self, mongo_client=None):
        self.mongo_client = mongo_client if mongo_client is not None else settings.MONGO_CLIENT

    def _get_deleted_ids(self, db, collection_name, id_field):
        """
        Return IDs of documents tracked as deleted or pending deletion
        in the corresponding _<collection_name> restored collection.
        Returns an empty set if the restored collection does not exist.
        """
        if not collection_name or not id_field:
            return set()

        restored_collection_name = f"_{collection_name}"
        if restored_collection_name not in db.list_collection_names():
            return set()

        deleted_ids = {
            str(doc[id_field])
            for doc in db[restored_collection_name].find(
                {"operation_type": {"$in": ["deleted", "deletion_pending"]}},
                {id_field: 1, "_id": 0}
            )
            if doc.get(id_field)
        }

        if deleted_ids:
            logger.info(
                f"Excluding {len(deleted_ids)} deleted/pending-deletion records "
                f"from {collection_name} via {restored_collection_name}",
                extra={"operation": "FETCHDBFORDATE"}
            )

        return deleted_ids

    def fetch(self, date_str, entity_name, db_name=None):
        logger.info(f"Fetching data for date: {date_str}, entity: {entity_name}",extra={"operation":"FETCHDBFORDATE"})

        if db_name is None:
            db_name = get_latest_db(self.mongo_client, date_str)

        logger.info(f"Found database: {db_name}",extra={"operation":"FETCHDBFORDATE"})
        if not db_name:
            logger.warning(f"No database found for date: {date_str}",extra={"operation":"FETCHDBFORDATE"})
            return []

        db = self.mongo_client[db_name]

        if entity_name == "Auth Server":
            logger.info("Using AuthServerDataBuilder for nested data",extra={"operation":"FETCHDBFORDATE"})
            docs = AuthServer().build(db)

        elif entity_name == "Policy MFA":
            logger.info("Using PolicyMFADataBuilder for nested data",extra={"operation":"FETCHDBFORDATE"})
            docs = PolicyMFADataBuilder().build(db)

        elif entity_name == "App Signon Policy":
            logger.info("Using AppSignonPolicyDataBuilder for nested data",extra={"operation":"FETCHDBFORDATE"})
            docs = AppSignonPolicyDataBuilder().build(db)

        elif entity_name == "Policy Password":
            logger.info("Using PolicyPasswordDataBuilder for nested data",extra={"operation":"FETCHDBFORDATE"})
            docs = PolicyPasswordDataBuilder().build(db)

        elif entity_name == "Policy Profile Enrollment":
            logger.info("Using PolicyEnrollmentDataBuilder for nested data",extra={"operation":"FETCHDBFORDATE"})
            docs = PolicyEnrollmentDataBuilder().build(db)

        elif entity_name == "Policy Sign On":
            logger.info("Using PolicySignonDataBuilder for nested data",extra={"operation":"FETCHDBFORDATE"})
            docs = PolicySignonDataBuilder().build(db)

        elif entity_name == "Admin Role Custom":
            logger.info("Using AdminRoleCustomDataBuilder for nested data",extra={"operation":"FETCHDBFORDATE"})
            docs = AdminRoleCustomDataBuilder().build(db)

        else:
            collection_name = get_collection_name(entity_name)
            logger.info(f"Collection name for {entity_name}: {collection_name}",extra={"operation":"FETCHDBFORDATE"})
            if not collection_name:
                logger.warning(f"No collection name found for entity: {entity_name}",extra={"operation":"FETCHDBFORDATE"})
                return []

            docs = list(db[collection_name].find({}, {"_id": 0}))
            logger.info(f"Found {len(docs)} records in collection {collection_name}",extra={"operation":"FETCHDBFORDATE"})

        # Exclude documents tracked as deleted or pending deletion in the restored collection
        id_field = ENTITY_ID_MAPPING.get(entity_name)
        collection_name = get_collection_name(entity_name)
        excluded_ids = self._get_deleted_ids(db, collection_name, id_field)
        if excluded_ids:
            docs = [d for d in docs if str(d.get(id_field, "")) not in excluded_ids]
            logger.info(f"After exclusion: {len(docs)} records remain for {entity_name}", extra={"operation": "FETCHDBFORDATE"})

        return docs