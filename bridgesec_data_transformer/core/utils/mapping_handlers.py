import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# Configuration constants
MAPPED_ENTITIES_HELPERS = {
    "entities": {
        "okta_app_signon_policy", 
        "okta_policy_mfa",
        "okta_policy_password",
        "okta_policy_sign_on",
        "okta_policy_profile_enrollment"
    },
    "entity_mapped_collections": {
        "okta_app_signon_policy": "okta_app_signon_policy_rule",
        "okta_policy_mfa": "okta_policy_rule_mfa",
        "okta_policy_password": "okta_policy_rule_password",
        "okta_policy_sign_on": "okta_policy_rule_sign_on",
        "okta_policy_profile_enrollment": "okta_policy_rule_profile_enrollment"
    },
    "entity_subsets": {
        "okta_app_signon_policy": "policy_rules",
        "okta_policy_mfa": "mfa_rules",
        "okta_policy_password": "password_rules",
        "okta_policy_sign_on": "policy_signon_rules",
        "okta_policy_rule_sign_on": "okta_policy_rule_sign_on",
        "okta_policy_profile_enrollment": "policy_enrollment_rules"
    }
}

ID_KEYS = {
    "okta_user": "user_id",
    "okta_user_schema_property": "index",
    "okta_user_group_memberships": "user_id",
    "okta_user_base_schema_property": "index",
    "okta_user_admin_roles": "user_id",
    "okta_user_type": "user_type_id",

    "okta_auth_server": "auth_server_id",

    "okta_app_oauth": "app_id",
    "okta_app_saml": "app_id",
    "okta_app_signon_policy": "app_policy_id",
    "okta_app_signon_policy_rule": "policy_id",

    "okta_app_bookmark": "app_id",
    "okta_app_basic_auth": "app_id",
    "okta_app_swa": "app_id",
    "okta_app_three_field": "app_id",

    "okta_app_auto_login": "app_id",
    "okta_app_group_assignment": "app_id",
    "okta_app_group_assignments": "app_id",
    
    "okta_app_user": "app_id",

    "okta_group": "group_id",

    "okta_policy_mfa": "policy_id",
    "okta_policy_rule_mfa": "policy_rule_id",
    "okta_policy_password": "policy_id",
    "okta_policy_rule_password": "policy_id",
    "okta_policy_sign_on": "policy_signon_id",
    "okta_policy_rule_sign_on": "policy_id",
    "okta_policy_profile_enrollment": "policy_id",
}


def delete_ids(document):
    """
    Remove _id and clean values in a dictionary.
    """
    if not isinstance(document, dict):
        return document

    return {k: v for k, v in document.items() if k != "_id"}


def drop_mongo_id_list(docs):
    """
    Clean a list of mongo documents:
    - remove _id
    - convert "" and [] to None
    - handle nested structures
    """
    return [delete_ids(doc) for doc in docs]


def is_mapped_entity(collection_name: str) -> bool:
    """
    Check if a collection name is a mapped entity.

    Args:
        collection_name: The name of the collection to check

    Returns:
        True if the collection is a mapped entity, False otherwise
    """
    return collection_name in MAPPED_ENTITIES_HELPERS["entities"]