from . import mapping_handlers
import logging


logger = logging.getLogger(__name__)


def get_data(db, collection, modified_data, mapped=False, id_value=None) -> {}:
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
        id = mapping_handlers.ID_KEYS[collection]
        if not id_value:
            id_value = modified_data.get(id, None)
        print('collection: ', collection)
        print('id: ', id)
        if not mapped:
            data = collect.find_one({id: id_value})
            print('data: ', data)
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
        new_data = {**data, **modified_data}
        return new_data

    except Exception as err:
        logger.exception(f"Error occured {err}")


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
    print('mapped_collection: ', mapped_collection)
    parent_id_key = mapping_handlers.ID_KEYS[collection]
    print('parent_id_key: ', parent_id_key)
    subset_key = mapping_handlers.MAPPED_ENTITIES_HELPERS["entity_subsets"][collection]
    print('subset_key: ', subset_key)
    
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

    parent_data[subset_key] = clean_rules
    print('parent_data with subset_key: ', parent_data)
    
    return parent_data

    


# def get_mapped_collection(db, collection, modified_data) -> {}:
#     """Fetch the mapped collection from the database.

#     Args:
#         db (any): Database
#         collection (str): Collection name
#     Returns:
#         {}: Mapped collection data
#     """
#     new_collection = mapping_handlers.MAPPED_ENTITIES_HELPERS["entity_mapped_collections"][collection]

#     id = mapping_handlers.ID_KEYS[collection]

#     data = get_data(db, collection, modified_data, mapped=False)
#     print('data: ', data)
#     sub_data = get_data(db, new_collection, modified_data, True, data[id])
#     print('sub_data: ', sub_data)


