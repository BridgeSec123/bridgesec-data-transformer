from typing import Dict, Any, List, Optional
from pymongo import MongoClient
from django.conf import settings
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Import utility functions from core.utils
from core.utils.db_utils import get_collection_name, get_latest_db


class AdminRoleCustomDataBuilder:
    """
    Builds nested JSON per Admin Role Custom with resource sets.
    """

    def build(self, db):
        logger.info("Fetching collections for Admin Role Custom nested builder...")

        # Check available collections
        collections = db.list_collection_names()
        logger.info(f"Available collections: {collections}")

        # Directly retrieve already formatted docs (without _id)
        admin_roles = list(db["okta_admin_role_custom"].find({}, {"_id": 0}))
        resource_sets = list(db["okta_resource_set"].find({}, {"_id": 0}))

        logger.info(f"Found {len(admin_roles)} Admin Role Custom roles, {len(resource_sets)} resource sets")

        results = []
        for role in admin_roles:
            role_name = role.get("name")
            logger.info(f"Building nested data for Admin Role Custom: {role_name}")

            formatted = {
                **role,  # take all fields as already formatted in DB
                "resource_sets": [resource for resource in resource_sets if resource.get("role_id") == role_name],
            }

            logger.info(f"Admin Role Custom {role_name} has {len(formatted['resource_sets'])} resource sets")
            results.append(formatted)

        logger.info(f"Built nested Admin Role Custom data for {len(results)} roles")
        return {"admin_role_custom_list": results}