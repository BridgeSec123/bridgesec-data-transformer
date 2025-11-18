import logging

from entities.services.service_utils import fetch_collection

logger = logging.getLogger(__name__)


class AdminRoleCustomDataBuilder:
    """
    Builds nested JSON per Admin Role Custom with resource sets.
    Fetches data directly from DB collections without merging.
    """

    def build(self, db):
        logger.info("Fetching Admin Role Custom data from DB...")

        # Fetch parent roles from DB
        roles = fetch_collection(db, "okta_admin_role_custom")
        logger.info(f"Found {len(roles)} Admin Role Custom roles")

        # Fetch resource sets from DB
        all_resource_sets = fetch_collection(db, "okta_resource_set")
        logger.info(f"Found {len(all_resource_sets)} resource sets")

        # Build nested structure
        results = []
        for role in roles:
            role_id = role.get("custom_role_id") or role.get("name")

            # Find all resource sets for this role
            resource_sets = [resource for resource in all_resource_sets if resource.get("role_id") == role_id]

            formatted = {
                **role,  # Include all role fields
                "resource_sets": resource_sets,
            }

            logger.info(f"Admin Role Custom {role_id} has {len(resource_sets)} resource sets")
            results.append(formatted)

        logger.info(f"Built nested Admin Role Custom data for {len(results)} roles")
        return results
