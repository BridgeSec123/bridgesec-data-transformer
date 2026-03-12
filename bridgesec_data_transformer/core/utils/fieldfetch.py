import json
import logging

from . import mapping_handlers

logger = logging.getLogger(__name__)

get_all_data = lambda db, collection: list(db[collection].find({}))

def clean_data(datas):
    pops = ["operation_type", "created_at", "updated_at", "restored_by", "restored_at", "restored_from", "unique_id"]
    for data in datas:
        for pop in pops:
            data.pop(pop, None)
    return datas

def get_data(db, collection, modified_data = None, mapped=False, id_value=None) -> {}:
    """Fetch the data from the db to return the original data

    Args:
        db (any): Database
        collection (tring): Collection name
        modified_data (Dictionary): Modified datas with the required fields

    Returns:
        dictionary: Original data as a dictionary

    """    
    collect = db[collection]
    try:
        id = mapping_handlers.ID_KEYS[collection]  # To handle collections with leading underscore
        if not id_value and modified_data:
            id_value = modified_data.get(id, None)
        if not mapped:
            data = collect.find_one({id: id_value})
            data = transform_data(collection, data)
        if mapped and id:
            data = list(collect.find({id: id_value}))
        return data
    except Exception as err:
        logger.exception(f"{err}")
        return None


def get_collection(db, collection, modified_data) -> {}:
    """To get the Original data and the modified data with the required Fields

    Args:
        db (any): Database
        collection (tring): Collection name
        modified_data (Dictionary): Modified datas with the required fields

    Returns:
        {}: the original data
        {}: the modified data
    """
    try:
        data = mapping_handlers.delete_ids(get_data(db, collection, modified_data))
        modified_data = transform_data(collection, modified_data)

        # If data is None (record doesn't exist in source DB), treat as new record
        if data is None:
            logger.info(f"Record not found in source DB for {collection}, treating as new record")
            return modified_data

        new_data = {**data, **modified_data}
        return new_data

    except Exception as err:
        logger.exception(f"Error occured {err}")
        # Return modified_data as fallback if error occurs
        return modified_data


def get_mapped_collection(db, collection, modified_data):
    """
    Fetch and merge mapped parent + rule entities (self-contained, no merge_mapped_fields).
    
    Args:
        db: Database connection
        collection (str): Parent collection name (e.g., "okta_policy_mfa")
        modified_data (dict): Modified data with ID and optional rule updates
        
    Returns:
        dict: {"parent": merged_parent, "rules": full_merged_rules}
    """
    # Get configuration from helpers
    mapped_collection = mapping_handlers.MAPPED_ENTITIES_HELPERS["entity_mapped_collections"][collection]
    parent_id_key = mapping_handlers.ID_KEYS[collection]
    subset_key = mapping_handlers.MAPPED_ENTITIES_HELPERS["entity_subsets"][collection]
    
    # Fetch parent document
    parent_data = mapping_handlers.delete_ids(get_data(db, collection, modified_data))
    if not parent_data:
        logger.warning(f"Parent document not found for {collection}: {modified_data.get(parent_id_key)}")
        return {"parent": None, "rules": []}
    
    # Fetch all rules for this parent
    rule_data = get_data(db, mapped_collection, modified_data, mapped=True, id_value=parent_data[parent_id_key])
    all_rules = rule_data or []
    
    # Get partial rules from incoming data
    partial_rules = modified_data.get(subset_key, [])  # e.g., "policy_rules", "mfa_rules"

    # Clean all rules
    clean_rules = mapping_handlers.drop_mongo_id_list(all_rules)

    parent_data = {**parent_data, **modified_data}

    # Only use original rules if user didn't provide modified rules
    if not partial_rules:
        parent_data[subset_key] = clean_rules
    # Otherwise, keep the modified rules from the user (already in parent_data from merge above)

    return parent_data

def transform_data(collection_name, modified_data):
    """
    Transform data based on whether the collection is mapped or not.

    Args:
        collection_name (str): The name of the collection
        modified_data (dict): The modified data to transform

    Returns:
        dict: The transformed data
    """

    none_fields = mapping_handlers.NONE_FIELD_LISTS.get(collection_name, [])
    if not none_fields:
        return modified_data

    def is_empty(value):
        return value in (None, "", [], "{}", {}, [{}])
    
    if collection_name == "okta_policy_mfa" and is_empty(modified_data.get("external_idps")):
        modified_data["external_idps"] = []
        for field in mapping_handlers.NONE_FIELD_LISTS.get("okta_mfa_authenticator", []):
            modified_data.pop(field, None)
        
    for field, default_value in none_fields.items():
        if is_empty(modified_data.get(field)):
            modified_data[field] = default_value

    return modified_data