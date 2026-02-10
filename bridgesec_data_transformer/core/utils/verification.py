"""
Generic verification functions for deletion operations.

This module provides comprehensive verification that resources are properly
deleted from:
1. Okta API (should return 404)
2. MongoDB (marked as operation_type="deleted")
3. Terraform state files in Supabase (resource removed)

Works with ANY entity type without entity-specific code.
"""

import logging
import requests
from typing import Dict, List, Any, Optional
from django.conf import settings

logger = logging.getLogger(__name__)


def verify_deletion_complete(
    entity_type: str,
    entity_record: Dict[str, Any],
    deletion_results: Dict[str, Any],
    access_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Main verification function - runs all 3 checks after deletion.

    Args:
        entity_type: Entity type (e.g., "App Oauth", "Policy MFA")
        entity_record: Dict with entity IDs and data
        deletion_results: Response from Terraform deletion
        access_token: Okta OAuth access token (optional)

    Returns:
        {
            "verified": True/False,
            "entity_type": "App Oauth",
            "entity_record": {...},
            "checks": {
                "okta_api": {"status": "pass/fail/error", "details": "..."},
                "mongodb": {"status": "pass/fail/warning", "details": "..."},
                "terraform_state": {"status": "pass/fail/error", "details": "..."}
            },
            "orphaned_dependencies": [...]
        }

    Example:
        >>> verify_deletion_complete(
        ...     entity_type="App Oauth",
        ...     entity_record={"app_id": "0oa123"},
        ...     deletion_results={"success": True},
        ...     access_token="token"
        ... )
        {
            "verified": True,
            "checks": {
                "okta_api": {"status": "pass", "details": "..."},
                "mongodb": {"status": "pass", "details": "..."},
                "terraform_state": {"status": "pass", "details": "..."}
            },
            "orphaned_dependencies": []
        }
    """
    logger.info(f"=" * 80)
    logger.info(f"DELETION VERIFICATION: {entity_type}")
    logger.info(f"=" * 80)

    verification_results = {
        "verified": False,
        "entity_type": entity_type,
        "entity_record": entity_record,
        "checks": {},
        "orphaned_dependencies": []
    }

    # CHECK 1: Okta API Verification
    logger.info("Check 1: Verifying deletion in Okta API...")
    if access_token:
        okta_check = verify_okta_deletion(entity_type, entity_record, access_token)
    else:
        okta_check = {
            "status": "warning",
            "details": "No access token provided, skipping Okta API check"
        }
    verification_results["checks"]["okta_api"] = okta_check
    _log_check_result("Okta API", okta_check)

    # CHECK 2: MongoDB Verification
    logger.info("Check 2: Verifying deletion in MongoDB...")
    mongodb_check = verify_mongodb_deletion(entity_type, entity_record)
    verification_results["checks"]["mongodb"] = mongodb_check
    _log_check_result("MongoDB", mongodb_check)

    # CHECK 3: Terraform State Verification
    logger.info("Check 3: Verifying deletion from Terraform state...")
    state_check = verify_terraform_state_deletion(
        entity_type, entity_record, deletion_results
    )
    verification_results["checks"]["terraform_state"] = state_check
    _log_check_result("Terraform State", state_check)

    # CHECK 4: Find orphaned dependencies
    logger.info("Check 4: Looking for orphaned dependencies...")
    orphaned = find_orphaned_dependencies(entity_type, entity_record, deletion_results)
    verification_results["orphaned_dependencies"] = orphaned

    if orphaned:
        logger.warning(f"⚠️  Found {len(orphaned)} orphaned dependency resources")
        for orphan in orphaned:
            logger.warning(f"   - {orphan['dependency_type']}: {orphan['resource_key']}")
    else:
        logger.info("✅ No orphaned dependencies found")

    # Determine overall verification status
    verification_results["verified"] = _is_verification_successful(
        verification_results["checks"],
        orphaned
    )

    logger.info(f"=" * 80)
    logger.info(f"VERIFICATION RESULT: {'✅ VERIFIED' if verification_results['verified'] else '❌ FAILED'}")
    logger.info(f"=" * 80)

    return verification_results


def verify_okta_deletion(
    entity_type: str,
    entity_record: Dict[str, Any],
    access_token: str
) -> Dict[str, str]:
    """
    CHECK 1: Verify resource deleted from Okta API (should return 404).

    Args:
        entity_type: Entity type (e.g., "App Oauth")
        entity_record: Dict with entity IDs
        access_token: Okta OAuth access token

    Returns:
        {"status": "pass/fail/error", "details": "..."}

    Example:
        >>> verify_okta_deletion("App Oauth", {"app_id": "0oa123"}, "token")
        {"status": "pass", "details": "OAuth Application not found in Okta (expected after deletion)"}
    """
    from core.utils.okta_endpoints import (
        get_okta_api_endpoint,
        extract_id_params_from_record,
        get_entity_display_name
    )

    okta_domain = settings.OKTA_API_URL

    try:
        # Extract ID parameters from entity record
        id_params = extract_id_params_from_record(entity_type, entity_record)

        if not id_params:
            return {
                "status": "error",
                "details": f"Could not extract ID parameters from record: {entity_record}"
            }

        # Build endpoint URL using generic mapping
        endpoint = get_okta_api_endpoint(entity_type, **id_params)
        full_url = f"{okta_domain}{endpoint}"

        # Make API request
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }

        logger.debug(f"Checking Okta API: GET {full_url}")
        response = requests.get(full_url, headers=headers, timeout=10)

        entity_display = get_entity_display_name(entity_type)

        if response.status_code == 404:
            return {
                "status": "pass",
                "details": f"{entity_display} not found in Okta (expected after deletion)"
            }
        elif response.status_code == 200:
            return {
                "status": "fail",
                "details": f"{entity_display} still exists in Okta (deletion may have failed)"
            }
        else:
            return {
                "status": "error",
                "details": f"Unexpected response from Okta API: {response.status_code}"
            }

    except Exception as e:
        logger.error(f"Error checking Okta deletion: {e}")
        return {
            "status": "error",
            "details": f"Error checking Okta API: {str(e)}"
        }


def verify_mongodb_deletion(
    entity_type: str,
    entity_record: Dict[str, Any]
) -> Dict[str, str]:
    """
    CHECK 2: Verify deletion recorded in MongoDB.

    Checks if record exists with operation_type="deleted".

    Args:
        entity_type: Entity type
        entity_record: Dict with entity IDs

    Returns:
        {"status": "pass/warning/error", "details": "..."}

    Example:
        >>> verify_mongodb_deletion("App Oauth", {"app_id": "0oa123"})
        {"status": "pass", "details": "Record marked as deleted in MongoDB"}
    """
    from core.utils.db_utils import get_latest_db
    from core.utils.collection_mapping import ENTITY_ID_MAPPING
    from core.utils.db_utils import get_collection_name

    mongo_client = settings.MONGO_CLIENT

    try:
        # Get current database (today's DB)
        from datetime import datetime
        today_str = datetime.now().strftime("%Y-%m-%d")
        db_name = get_latest_db(mongo_client, today_str)

        if not db_name:
            return {
                "status": "warning",
                "details": "No current database found for MongoDB check"
            }

        db = mongo_client[db_name]

        # Get collection name for this entity
        collection_name = get_collection_name(entity_type)

        if not collection_name:
            return {
                "status": "warning",
                "details": f"No collection mapping found for {entity_type}"
            }

        # Get restored collection (with _ prefix)
        restored_collection_name = f"_{collection_name}"

        if restored_collection_name not in db.list_collection_names():
            return {
                "status": "warning",
                "details": f"No restored collection found ({restored_collection_name})"
            }

        restored_collection = db[restored_collection_name]

        # Get ID field for this entity
        id_field = ENTITY_ID_MAPPING.get(entity_type)

        if not id_field:
            return {
                "status": "warning",
                "details": f"No ID field mapping found for {entity_type}"
            }

        # Extract ID value
        id_value = entity_record.get(id_field)

        if not id_value:
            # Try alternate extraction
            from core.utils.okta_endpoints import extract_id_params_from_record
            id_params = extract_id_params_from_record(entity_type, entity_record)
            id_value = id_params.get("id")

        if not id_value:
            return {
                "status": "error",
                "details": f"Missing ID field '{id_field}' in entity record"
            }

        # Check for deleted record
        deleted_record = restored_collection.find_one(
            {
                id_field: id_value,
                "operation_type": "deleted"
            },
            {"_id": 0}
        )

        if deleted_record:
            return {
                "status": "pass",
                "details": f"Record marked as deleted in MongoDB ({restored_collection_name})"
            }
        else:
            # Check if record exists with other operation_type
            any_record = restored_collection.find_one({id_field: id_value}, {"_id": 0})

            if any_record:
                op_type = any_record.get("operation_type", "unknown")
                return {
                    "status": "fail",
                    "details": f"Record exists in MongoDB but operation_type is '{op_type}' (expected 'deleted')"
                }
            else:
                return {
                    "status": "warning",
                    "details": "Record not found in MongoDB (may not have been restored previously)"
                }

    except Exception as e:
        logger.error(f"Error checking MongoDB deletion: {e}")
        return {
            "status": "error",
            "details": f"Error checking MongoDB: {str(e)}"
        }


def verify_terraform_state_deletion(
    entity_type: str,
    entity_record: Dict[str, Any],
    deletion_results: Dict[str, Any]
) -> Dict[str, str]:
    """
    CHECK 3: Verify resource removed from Terraform state file in Supabase.

    Args:
        entity_type: Entity type
        entity_record: Dict with entity IDs
        deletion_results: Results from Terraform destroy operation

    Returns:
        {
            "status": "pass/fail/error",
            "details": "...",
            "dependencies_checked": [...]  # Optional
        }

    Example:
        >>> verify_terraform_state_deletion(
        ...     "App Oauth",
        ...     {"app_id": "0oa123"},
        ...     {"success": True}
        ... )
        {
            "status": "pass",
            "details": "Resource removed from terraform state (app-modules)",
            "dependencies_checked": [...]
        }
    """
    from core.utils.supabase_state_utils import (
        get_deployment_for_entity,
        get_state_file_from_supabase,
        check_resource_in_state
    )
    from core.utils.collection_mapping import ENTITY_ID_MAPPING

    try:
        # Get deployment name for this entity type
        deployment = get_deployment_for_entity(entity_type)

        if not deployment:
            return {
                "status": "warning",
                "details": f"No deployment configuration found for {entity_type}"
            }

        # Fetch state file from Supabase
        logger.debug(f"Fetching state file for deployment: {deployment}")
        state_data = get_state_file_from_supabase(deployment)

        if not state_data:
            return {
                "status": "warning",
                "details": f"State file not found for deployment '{deployment}' (may be new deployment)"
            }

        # Build resource key
        id_field = ENTITY_ID_MAPPING.get(entity_type)
        if not id_field:
            return {
                "status": "error",
                "details": f"No ID field mapping found for {entity_type}"
            }

        resource_id = entity_record.get(id_field)
        if not resource_id:
            return {
                "status": "error",
                "details": f"Missing {id_field} in entity record"
            }

        # Convert entity type to Terraform resource type
        # E.g., "App Oauth" → "okta_app_oauth"
        terraform_resource_type = _get_terraform_resource_type(entity_type)

        # Check if resource exists in state
        resource_exists = check_resource_in_state(
            state_data,
            terraform_resource_type,
            resource_id
        )

        if not resource_exists:
            return {
                "status": "pass",
                "details": f"Resource removed from terraform state ({deployment})"
            }
        else:
            return {
                "status": "fail",
                "details": f"Resource still exists in terraform state file ({deployment}/{terraform_resource_type}/{resource_id})"
            }

    except Exception as e:
        logger.error(f"Error checking Terraform state: {e}")
        return {
            "status": "error",
            "details": f"Error checking Terraform state: {str(e)}"
        }


def find_orphaned_dependencies(
    entity_type: str,
    entity_record: Dict[str, Any],
    deletion_results: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Find dependencies that should have been deleted but still exist in state.

    Args:
        entity_type: Parent entity type
        entity_record: Parent entity record
        deletion_results: Terraform deletion results

    Returns:
        List of orphaned resources:
        [
            {
                "dependency_type": "okta_app_group_assignment",
                "parent_type": "App Oauth",
                "parent_id": "0oa123",
                "resource_key": "0oa123-00g456",
                "state_file": "app-modules"
            }
        ]

    Example:
        >>> find_orphaned_dependencies(
        ...     "App Oauth",
        ...     {"app_id": "0oa123"},
        ...     {"success": True}
        ... )
        []  # No orphans found
    """
    from core.utils.supabase_state_utils import (
        get_deployment_for_entity,
        get_state_file_from_supabase,
        get_dependent_resources_in_state
    )
    from core.utils.collection_mapping import ENTITY_ID_MAPPING

    orphaned = []

    try:
        # Get dependency configuration
        # TODO: Import APP_DEPENDENCY_MAPPING or create local version
        dependency_mapping = _get_dependency_mapping(entity_type)

        if not dependency_mapping:
            logger.debug(f"No dependencies defined for {entity_type}")
            return []

        # Get deployment and state file
        deployment = get_deployment_for_entity(entity_type)
        if not deployment:
            return []

        state_data = get_state_file_from_supabase(deployment)
        if not state_data:
            return []

        # Get parent ID
        id_field = ENTITY_ID_MAPPING.get(entity_type)
        parent_id = entity_record.get(id_field)

        if not parent_id:
            logger.warning(f"Cannot check orphans: missing {id_field}")
            return []

        # Check each dependency type
        terraform_parent_type = _get_terraform_resource_type(entity_type)

        for dep_config in dependency_mapping:
            dep_entity_type = dep_config.get("entity_type")
            terraform_dep_type = _get_terraform_resource_type(dep_entity_type)

            # Find dependent resources in state
            dependent_keys = get_dependent_resources_in_state(
                state_data,
                terraform_parent_type,
                parent_id,
                terraform_dep_type
            )

            if dependent_keys:
                logger.warning(
                    f"⚠️  Found {len(dependent_keys)} orphaned {dep_entity_type} resources "
                    f"still in state for {entity_type} [{parent_id}]"
                )

                for key in dependent_keys:
                    orphaned.append({
                        "dependency_type": dep_entity_type,
                        "parent_type": entity_type,
                        "parent_id": parent_id,
                        "resource_key": key,
                        "state_file": deployment
                    })

    except Exception as e:
        logger.error(f"Error finding orphaned dependencies: {e}")

    return orphaned


# ============================================
# HELPER FUNCTIONS
# ============================================

def _get_terraform_resource_type(entity_type: str) -> str:
    """
    Convert entity type to Terraform resource type.

    Args:
        entity_type: Entity type (e.g., "App Oauth", "Policy MFA")

    Returns:
        Terraform resource type (e.g., "okta_app_oauth", "okta_policy_mfa")

    Example:
        >>> _get_terraform_resource_type("App Oauth")
        "okta_app_oauth"
    """
    # Simple mapping
    mappings = {
        "App Oauth": "okta_app_oauth",
        "App Saml": "okta_app_saml",
        "App Swa": "okta_app_swa",
        "App Group Assignment": "okta_app_group_assignment",
        "App User": "okta_app_user",
        "Policy MFA": "okta_policy_mfa",
        "Policy Password": "okta_policy_password",
        "Policy Sign On": "okta_policy_signon",
        "Auth Server": "okta_auth_server",
        "Groups": "okta_group",
        "User": "okta_user",
        # Add more as needed
    }

    return mappings.get(entity_type, entity_type.lower().replace(" ", "_"))


def _get_dependency_mapping(entity_type: str) -> List[Dict[str, Any]]:
    """
    Get dependency configuration for entity type.

    Args:
        entity_type: Entity type

    Returns:
        List of dependency configurations

    Example:
        >>> _get_dependency_mapping("App Oauth")
        [
            {"entity_type": "App Group Assignment", "query_field": "app_id"},
            {"entity_type": "App User", "query_field": "app_id"}
        ]
    """
    # Hardcoded dependency mapping
    # TODO: Import from Terraform repo or create shared configuration
    mappings = {
        "App Oauth": [
            {"entity_type": "App Group Assignment", "query_field": "app_id"},
            {"entity_type": "App User", "query_field": "app_id"},
        ],
        "App Saml": [
            {"entity_type": "App Group Assignment", "query_field": "app_id"},
            {"entity_type": "App User", "query_field": "app_id"},
        ],
        "Policy MFA": [
            {"entity_type": "Policy Rule Mfa", "query_field": "policy_id"},
        ],
        "Auth Server": [
            {"entity_type": "Auth Server Scopes", "query_field": "auth_server_id"},
            {"entity_type": "Auth Server Claims", "query_field": "auth_server_id"},
        ],
    }

    return mappings.get(entity_type, [])


def _is_verification_successful(
    checks: Dict[str, Dict[str, str]],
    orphaned: List[Dict[str, Any]]
) -> bool:
    """
    Determine if verification passed overall.

    Args:
        checks: Dictionary of check results
        orphaned: List of orphaned dependencies

    Returns:
        True if verification passed, False otherwise

    Criteria for success:
    - All checks have status "pass" or "warning"
    - No orphaned dependencies found
    """
    # Check if any check failed or errored
    for check_name, result in checks.items():
        status = result.get("status")
        if status in ["fail", "error"]:
            return False

    # Check if orphans exist
    if orphaned:
        return False

    return True


def _log_check_result(check_name: str, result: Dict[str, str]) -> None:
    """Helper to log check results with appropriate emoji."""
    status = result.get("status")
    details = result.get("details")

    if status == "pass":
        logger.info(f"   ✅ {check_name}: {details}")
    elif status == "fail":
        logger.error(f"   ❌ {check_name}: {details}")
    elif status == "warning":
        logger.warning(f"   ⚠️  {check_name}: {details}")
    else:  # error
        logger.error(f"   🚫 {check_name}: {details}")


# ============================================
# DELETION PREVIEW (for future use)
# ============================================

def get_deletion_preview(
    entity_type: str,
    entity_record: Dict[str, Any],
    access_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Preview what will be deleted (dry-run).

    NOT YET IMPLEMENTED - placeholder for future enhancement.

    Args:
        entity_type: Entity type
        entity_record: Entity record with IDs
        access_token: Optional access token

    Returns:
        {
            "parent": {...},
            "dependencies": {...},
            "total_resources_to_delete": 5
        }
    """
    # TODO: Implement deletion preview
    raise NotImplementedError("Deletion preview not yet implemented")
