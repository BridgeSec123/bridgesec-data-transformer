from typing import Dict, Any, List, Optional
from pymongo import MongoClient
from django.conf import settings
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Import utility functions from core.utils
from core.utils.db_utils import get_collection_name, get_latest_db
from .auth_server_service import AuthServer
from .policy_mfa_service import PolicyMFADataBuilder
from .app_signon_policy_service import AppSignonPolicyDataBuilder
from .policy_password_service import PolicyPasswordDataBuilder
from .policy_enrollment_service import PolicyEnrollmentDataBuilder
from .policy_signon_service import PolicySignonDataBuilder
from .admin_role_custom_service import AdminRoleCustomDataBuilder


class EntityDataService:
    def __init__(self):
        self.mongo_client = MongoClient(settings.MONGO_URI)

    def fetch(self, date_str, entity_name):
        logger.info(f"Fetching data for date: {date_str}, entity: {entity_name}",extra={"operation":"FETCHDBFORDATE"})

        db_name = get_latest_db(self.mongo_client, date_str)
        logger.info(f"Found database: {db_name}",extra={"operation":"FETCHDBFORDATE"})
        if not db_name:
            logger.warning(f"No database found for date: {date_str}",extra={"operation":"FETCHDBFORDATE"})
            return []

        db = self.mongo_client[db_name]

        if entity_name == "Auth Server":
            logger.info("Using AuthServerDataBuilder for nested data",extra={"operation":"FETCHDBFORDATE"})
            return AuthServer().build(db)

        if entity_name == "Policy MFA":
            logger.info("Using PolicyMFADataBuilder for nested data",extra={"operation":"FETCHDBFORDATE"})
            return PolicyMFADataBuilder().build(db)

        if entity_name == "App Signon Policy":
            logger.info("Using AppSignonPolicyDataBuilder for nested data",extra={"operation":"FETCHDBFORDATE"})
            return AppSignonPolicyDataBuilder().build(db)

        if entity_name == "Policy Password":
            logger.info("Using PolicyPasswordDataBuilder for nested data",extra={"operation":"FETCHDBFORDATE"})
            return PolicyPasswordDataBuilder().build(db)

        if entity_name == "Policy Profile Enrollment":
            logger.info("Using PolicyEnrollmentDataBuilder for nested data",extra={"operation":"FETCHDBFORDATE"})
            return PolicyEnrollmentDataBuilder().build(db)

        if entity_name == "Policy Sign On":
            logger.info("Using PolicySignonDataBuilder for nested data",extra={"operation":"FETCHDBFORDATE"})
            return PolicySignonDataBuilder().build(db)

        if entity_name == "Admin Role Custom":
            logger.info("Using AdminRoleCustomDataBuilder for nested data",extra={"operation":"FETCHDBFORDATE"})
            return AdminRoleCustomDataBuilder().build(db)

        collection_name = get_collection_name(entity_name)
        logger.info(f"Collection name for {entity_name}: {collection_name}",extra={"operation":"FETCHDBFORDATE"})
        if not collection_name:
            logger.warning(f"No collection name found for entity: {entity_name}",extra={"operation":"FETCHDBFORDATE"})
            return []

        result = list(db[collection_name].find({}, {"_id": 0}))
        logger.info(f"Found {len(result)} records in collection {collection_name}",extra={"operation":"FETCHDBFORDATE"})
        return result