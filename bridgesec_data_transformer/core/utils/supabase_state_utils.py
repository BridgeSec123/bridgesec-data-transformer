"""
Supabase state file utilities for Terraform state verification.

This module provides access to Terraform state files stored in Supabase storage.
Used for verifying that resources are properly deleted from Terraform state.

CONFIGURATION REQUIRED:
Add these to your .env file:
    SUPABASE_URL=https://your-project.supabase.co
    SUPABASE_KEY=your-anon-key-here
    SUPABASE_BUCKET=terraform-states

State File Structure in Supabase:
    supabase://terraform-states/deployments/app-modules/terraform.tfstate
    supabase://terraform-states/deployments/policies/terraform.tfstate
    supabase://terraform-states/deployments/groups/terraform.tfstate
"""

import json
import logging
from typing import Dict, List, Optional, Any
from django.conf import settings

logger = logging.getLogger(__name__)

# Supabase client (lazy loaded)
_supabase_client = None


def get_supabase_client():
    """
    Get or create Supabase client.

    Returns:
        Supabase client instance

    Raises:
        ImportError: If supabase-py not installed
        ValueError: If Supabase configuration missing
    """
    global _supabase_client

    if _supabase_client is not None:
        return _supabase_client

    try:
        from supabase import create_client, Client
    except ImportError:
        raise ImportError(
            "supabase-py package not installed. "
            "Install with: pip install supabase"
        )

    # Get configuration from settings
    supabase_url = getattr(settings, 'SUPABASE_URL', None)
    supabase_key = getattr(settings, 'SUPABASE_KEY', None)

    if not supabase_url or not supabase_key:
        raise ValueError(
            "Supabase configuration missing. Add SUPABASE_URL and SUPABASE_KEY to settings.py"
        )

    _supabase_client = create_client(supabase_url, supabase_key)
    logger.info("Supabase client initialized")

    return _supabase_client


def get_state_file_from_supabase(deployment_name: str) -> Optional[Dict[str, Any]]:
    """
    Fetch Terraform state file from Supabase storage.

    Args:
        deployment_name: Deployment name (e.g., "app-modules", "policies")

    Returns:
        Parsed state file JSON or None if not found

    Example:
        >>> state = get_state_file_from_supabase("app-modules")
        >>> state["version"]
        4
        >>> state["terraform_version"]
        "1.5.0"
    """
    try:
        client = get_supabase_client()
        bucket_name = getattr(settings, 'SUPABASE_BUCKET', 'terraform-states')

        # Build file path: deployments/{deployment_name}/terraform.tfstate
        file_path = f"deployments/{deployment_name}/terraform.tfstate"

        logger.debug(f"Fetching state file from Supabase: {bucket_name}/{file_path}")

        # Download file from Supabase storage
        response = client.storage.from_(bucket_name).download(file_path)

        if not response:
            logger.warning(f"State file not found: {file_path}")
            return None

        # Parse JSON
        state_data = json.loads(response)
        logger.info(f"Successfully fetched state file: {file_path} ({len(response)} bytes)")

        return state_data

    except Exception as e:
        logger.error(f"Error fetching state file from Supabase: {e}")
        return None


def check_resource_in_state(
    state_data: Dict[str, Any],
    resource_type: str,
    resource_key: str
) -> bool:
    """
    Check if a resource exists in Terraform state.

    Args:
        state_data: Parsed state file JSON
        resource_type: Terraform resource type (e.g., "okta_app_oauth")
        resource_key: Resource identifier (e.g., "0oa123" or "0oa123-00g456")

    Returns:
        True if resource found in state, False if deleted

    Example:
        >>> state = get_state_file_from_supabase("app-modules")
        >>> check_resource_in_state(state, "okta_app_oauth", "0oa123")
        False  # Resource was deleted
    """
    if not state_data:
        logger.warning("No state data provided")
        return False

    try:
        resources = state_data.get("resources", [])

        for resource in resources:
            if resource.get("type") != resource_type:
                continue

            # Check all instances within this resource
            instances = resource.get("instances", [])
            for instance in instances:
                # Resource key can be in different formats
                # 1. Simple key: resource name matches key
                # 2. Indexed key: resource name + index key

                instance_key = instance.get("index_key")

                # Handle different key formats
                if instance_key == resource_key:
                    return True

                # Check resource name as well (for non-indexed resources)
                resource_name = resource.get("name", "")
                if resource_name == resource_key:
                    return True

                # Check attributes for ID fields
                attributes = instance.get("attributes", {})
                if attributes.get("id") == resource_key:
                    return True

        return False

    except Exception as e:
        logger.error(f"Error checking resource in state: {e}")
        return False


def list_resources_in_state(
    state_data: Dict[str, Any],
    resource_type: Optional[str] = None
) -> List[str]:
    """
    List all resources of a specific type in state file.

    Args:
        state_data: Parsed state file JSON
        resource_type: Optional filter by resource type

    Returns:
        List of resource keys

    Example:
        >>> state = get_state_file_from_supabase("app-modules")
        >>> list_resources_in_state(state, "okta_app_oauth")
        ["0oa123", "0oa456", "0oa789"]
    """
    if not state_data:
        return []

    try:
        resources = state_data.get("resources", [])
        resource_keys = []

        for resource in resources:
            # Filter by type if specified
            if resource_type and resource.get("type") != resource_type:
                continue

            instances = resource.get("instances", [])
            for instance in instances:
                # Try to get resource key
                key = (
                    instance.get("index_key") or
                    instance.get("attributes", {}).get("id") or
                    resource.get("name")
                )

                if key:
                    resource_keys.append(key)

        return resource_keys

    except Exception as e:
        logger.error(f"Error listing resources in state: {e}")
        return []


def get_deployment_for_entity(entity_type: str) -> Optional[str]:
    """
    Map entity type to deployment/state file name.

    Uses the COLLECTION_STATE_MAP from the Terraform repo to determine
    which deployment a given entity belongs to.

    Args:
        entity_type: Entity type (e.g., "App Oauth", "Policy MFA")

    Returns:
        Deployment name (e.g., "app-modules", "policies") or None

    Example:
        >>> get_deployment_for_entity("App Oauth")
        "app-modules"

        >>> get_deployment_for_entity("Policy MFA")
        "policies"
    """
    # TODO: Import COLLECTION_STATE_MAP from Terraform repo or create local mapping
    # For now, use hardcoded mapping

    entity_to_deployment = {
        # Applications
        "App Oauth": "app-modules",
        "App Saml": "app-modules",
        "App Swa": "app-modules",
        "App Bookmark": "app-modules",
        "App Auto Login": "app-modules",
        "App Basic Auth": "app-modules",
        "App Three Field": "app-modules",
        "App Secure Password Store": "app-modules",
        "App Group Assignment": "app-modules",
        "App User": "app-modules",

        # Policies
        "Policy MFA": "policies",
        "Policy Password": "policies",
        "Policy Sign On": "policies",
        "Policy Profile Enrollment": "policies",

        # Groups
        "Groups": "groups",
        "Group Rules": "groups",

        # Users
        "User": "users",
        "User Type": "users",

        # Auth Servers
        "Auth Server": "auth-servers",

        # Identity Providers
        "IDP OIDC": "identity-providers",
        "IDP SAML": "identity-providers",
        "IDP SOCIAL": "identity-providers",

        # Security
        "Authenticator": "security",
        "Brand": "security",
        "Network Zone": "security",
        "Trusted Origin": "security",
        "Behavior": "security",
    }

    deployment = entity_to_deployment.get(entity_type)

    if not deployment:
        logger.warning(f"No deployment mapping found for entity type: {entity_type}")

    return deployment


def get_dependent_resources_in_state(
    state_data: Dict[str, Any],
    parent_type: str,
    parent_id: str,
    dependency_type: str
) -> List[str]:
    """
    Find dependent resources that reference a parent resource.

    Args:
        state_data: Parsed state file JSON
        parent_type: Parent resource type (e.g., "okta_app_oauth")
        parent_id: Parent resource ID (e.g., "0oa123")
        dependency_type: Dependency resource type (e.g., "okta_app_group_assignment")

    Returns:
        List of dependent resource keys that reference the parent

    Example:
        >>> state = get_state_file_from_supabase("app-modules")
        >>> get_dependent_resources_in_state(
        ...     state, "okta_app_oauth", "0oa123", "okta_app_group_assignment"
        ... )
        ["0oa123-00g456", "0oa123-00g789"]
    """
    if not state_data:
        return []

    try:
        resources = state_data.get("resources", [])
        dependent_keys = []

        for resource in resources:
            if resource.get("type") != dependency_type:
                continue

            instances = resource.get("instances", [])
            for instance in instances:
                attributes = instance.get("attributes", {})

                # Check if this dependency references the parent
                # Common patterns:
                # - app_id == parent_id (for app dependencies)
                # - policy_id == parent_id (for policy dependencies)
                # - auth_server_id == parent_id (for auth server dependencies)

                if (
                    attributes.get("app_id") == parent_id or
                    attributes.get("policy_id") == parent_id or
                    attributes.get("auth_server_id") == parent_id or
                    attributes.get("group_id") == parent_id or
                    attributes.get("user_id") == parent_id
                ):
                    key = (
                        instance.get("index_key") or
                        attributes.get("id") or
                        resource.get("name")
                    )
                    if key:
                        dependent_keys.append(key)

        return dependent_keys

    except Exception as e:
        logger.error(f"Error finding dependent resources: {e}")
        return []
