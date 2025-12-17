"""
Utility functions for restore operations.
Handles both simple entities and entities with nested data (builders).
"""
import copy
import logging
from datetime import datetime

from core.utils.collection_mapping import ENTITY_ID_MAPPING
from core.utils.constants import (ENTITY_TARGET_FIELD_MAP,
                                  SINGLETON_RESOURCE_IDENTIFIERS)
from core.utils.nested_mapping import (NESTED_FIELD_COLLECTIONS,
                                       NESTED_FIELD_ID_MAPPING)

from core.utils.mapping_handlers import MAPPED_ENTITIES_HELPERS
from django.utils.text import slugify

logger = logging.getLogger(__name__)


def _extract_ids_from_data(data_records, field_name, include_nested=False):
    """
    Extract unique IDs from data records.

    Args:
        data_records: List of records
        field_name: Field name to extract
        include_nested: Whether to search nested arrays

    Returns:
        Set of unique ID values
    """
    ids = set()

    for record in data_records:
        # Extract from parent level
        if field_name in record and record[field_name]:
            ids.add(str(record[field_name]))

        # Extract from nested arrays if requested
        if include_nested:
            for value in record.values():
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict) and field_name in item and item[field_name]:
                            ids.add(str(item[field_name]))

    return ids

def _store_collection_simple(db, entity_name, collection_name, records, unique_id=None):
    """
    Store records without restore metadata.
    For creation flow only.
    """

    collection = db[f"_{collection_name}"]

    for rec in records:
        rec_copy = copy.deepcopy(rec)
        # rec_copy.pop("_id", None)
        rec_copy["operation_type"] = "created"
        rec_copy["created_at"] = str(datetime.utcnow())
        if unique_id:
            rec_copy["unique_id"] = unique_id

        collection.insert_one(rec_copy)

    logger.info(f"Stored {len(records)} records in '{collection_name}' for entity {entity_name}")


def _store_collection(db, entity_name, collection_name, data, restored_by, source_db_name):
    """
    Internal helper to store data in a restored collection with metadata.
    Uses upsert to prevent duplicates and preserve version history.

    Args:
        db: MongoDB database instance
        entity_name: Entity name
        collection_name: Collection name
        data: Data to store
        restored_by: User who performed the restore
        source_db_name: Source database name
    """
    if not data:
        logger.warning(f"No data to store for _{collection_name}")
        return

    # Prepare metadata
    restored_at = datetime.now().strftime("%H:%M:%S")
    restored_collection_name = f"_{collection_name}"
    restored_collection = db[restored_collection_name]

    # Get ID field for upsert
    # Check if this is a nested collection
    id_field = None
    nested_mapping = NESTED_FIELD_COLLECTIONS.get(entity_name, {})

    # Find if this collection is a nested collection
    for nested_field, nested_collection_name in nested_mapping.items():
        if nested_collection_name == collection_name:
            # This is a nested collection - use child_id_field
            id_field = NESTED_FIELD_ID_MAPPING.get(nested_field, {}).get("child_id_field")
            logger.info(f"Detected nested collection {collection_name}, using child_id_field: {id_field}")
            break

    # If not a nested collection, use the entity's ID field
    if not id_field:
        id_field = ENTITY_ID_MAPPING.get(entity_name)

    if id_field:
        # Use upsert strategy (recommended)
        upsert_count = 0
        for doc in data:
            # Add metadata
            doc["operation_type"] = "restored"
            doc["restored_by"] = restored_by
            doc["restored_from"] = source_db_name
            doc["restored_at"] = restored_at
            doc.pop("_id", None)  # Remove MongoDB _id

            id_value = doc.get(id_field)
            if id_value:
                # Upsert: update if exists, insert if not
                restored_collection.replace_one(
                    {id_field: id_value},
                    doc,
                    upsert=True
                )
                upsert_count += 1
            else:
                logger.warning(f"Document missing {id_field} field, skipping")

        logger.info(f"Upserted {upsert_count} records to {restored_collection_name}")
    else:
        # Fallback: replace all data (dangerous - deletes existing)
        logger.warning(f"No ID field defined for {entity_name}, using replace_all strategy")

        # Add metadata to all records
        for doc in data:
            doc["restored_by"] = restored_by
            doc["restored_from"] = source_db_name
            doc["restored_at"] = restored_at
            doc.pop("_id", None)

        # Delete existing and insert new
        delete_result = restored_collection.delete_many({})
        logger.info(f"Deleted {delete_result.deleted_count} existing records from {restored_collection_name}")

        if data:
            restored_collection.insert_many(data)
            logger.info(f"Inserted {len(data)} new records into {restored_collection_name}")


def store_restored_data_with_metadata(db, entity_name, collection_name, modified_data, restored_by, source_db_name):
    """
    Universal function to store restored data.
    Handles BOTH simple entities AND entities with nested data (builders).
    """
    logger.info(f"Storing {len(modified_data)} records for {entity_name}")

    # Check if this entity has nested fields
    nested_mapping = NESTED_FIELD_COLLECTIONS.get(entity_name)

    if nested_mapping:
        # Entity with nested data - split into parent and nested collections
        accumulated_nested_data = {nested_collection_name: [] for nested_collection_name in nested_mapping.values()}
        flattened_parent_data = []

        for parent_record in modified_data:
            parent_copy = copy.deepcopy(parent_record)

            # Extract nested arrays
            for nested_field, nested_collection_name in nested_mapping.items():
                nested_array = parent_record.get(nested_field, [])
                if nested_array:
                    accumulated_nested_data[nested_collection_name].extend(nested_array)
                parent_copy.pop(nested_field, None)

            flattened_parent_data.append(parent_copy)

        # Store nested collections
        for nested_collection_name, all_nested_records in accumulated_nested_data.items():
            if all_nested_records:
                _store_collection(db, entity_name, nested_collection_name,
                                all_nested_records, restored_by, source_db_name)

        # Store parent data
        _store_collection(db, entity_name, collection_name,
                        flattened_parent_data, restored_by, source_db_name)

        return flattened_parent_data

    else:
        # Simple entity - store as-is
        _store_collection(db, entity_name, collection_name,
                        modified_data, restored_by, source_db_name)
        return modified_data

def store_created_data(db, entity_name, collection_name, created_data):
    """
    Store newly created data without restore metadata.
    Handles simple and nested (builder-style) entities.
    """

    logger.info(f"Storing created data for {entity_name}: {len(created_data)} records")

    nested_mapping = NESTED_FIELD_COLLECTIONS.get(entity_name)

    if nested_mapping:
        # Has nested collections → split parent + nested
        accumulated_nested_data = {
            nested_collection_name: []
            for nested_collection_name in nested_mapping.values()
        }
        flattened_parent_data = []
        
        for parent_record in created_data:
            unique_fields = MAPPED_ENTITIES_HELPERS["entity_unique_fields"].get(collection_name, "")
            unique_id = slugify(parent_record.get(unique_fields, "")) if unique_fields else None
            parent_copy = copy.deepcopy(parent_record)

            for nested_field, nested_collection_name in nested_mapping.items():
                nested_array = parent_record.get(nested_field, [])
                if nested_array:
                    accumulated_nested_data[nested_collection_name].extend(nested_array)

                parent_copy.pop(nested_field, None)

            flattened_parent_data.append(parent_copy)

        # Store nested collections (no metadata)
        for nested_collection_name, records in accumulated_nested_data.items():
            if records:
                _store_collection_simple(db, entity_name, nested_collection_name, records, unique_id)

        # Store parent data
        _store_collection_simple(db, entity_name, collection_name, flattened_parent_data, unique_id)

        return flattened_parent_data

    else:
        # No nested data → store collection directly
        _store_collection_simple(db, entity_name, collection_name, created_data)
        return created_data
                                                     
def extract_terraform_target_params(collection_name, data_to_send):
    """Extract target field IDs and build parameters for Terraform API."""
    params = {"collection_name": collection_name}
    
    return params


def _get_latest_records_by_id(records, id_field):
    """Keep only the latest version of each record based on restored_at."""
    if not records:
        return []

    def parse_time(record):
        """Convert restored_at (HH:MM:SS) to seconds"""
        try:
            h, m, s = record.get("restored_at", "00:00:00").split(":")
            return int(h) * 3600 + int(m) * 60 + int(s)
        except:
            return 0

    # Group by ID and keep latest
    grouped = {}
    for record in records:
        record_id = str(record.get(id_field))
        if record_id:
            if record_id not in grouped or parse_time(record) > parse_time(grouped[record_id]):
                grouped[record_id] = record

    return list(grouped.values())


def rebuild_restored_data_with_nested_arrays(db, entity_name, collection_name, id_field):
    """
    Rebuild restored data with nested arrays.
    Returns only the LATEST version of each record.
    """
    nested_mapping = NESTED_FIELD_COLLECTIONS.get(entity_name)

    # Simple entity - fetch and return latest versions
    if not nested_mapping:
        coll_name = f"_{collection_name}"
        if coll_name in db.list_collection_names():
            all_data = list(db[coll_name].find({}, {"_id": 0}))
            return _get_latest_records_by_id(all_data, id_field)
        return []

    # Entity with nested data - rebuild
    parent_coll = f"_{collection_name}"
    if parent_coll not in db.list_collection_names():
        return []

    # Get latest parent records
    parent_data = _get_latest_records_by_id(
        list(db[parent_coll].find({}, {"_id": 0})), id_field
    )
    if not parent_data:
        return []

    # Map parents by ID
    parent_map = {str(r.get(id_field)): copy.deepcopy(r) for r in parent_data if r.get(id_field)}

    # Attach nested data
    from core.utils.nested_mapping import NESTED_FIELD_ID_MAPPING

    for nested_field, nested_coll_name in nested_mapping.items():
        nested_coll = f"_{nested_coll_name}"

        # Initialize empty arrays
        for parent in parent_map.values():
            parent[nested_field] = []

        if nested_coll not in db.list_collection_names():
            continue

        # Get nested ID field and latest records
        nested_id_field = NESTED_FIELD_ID_MAPPING.get(nested_field, {}).get("child_id_field", "id")
        nested_data = _get_latest_records_by_id(
            list(db[nested_coll].find({}, {"_id": 0})), nested_id_field
        )

        # Attach to parents
        for nested in nested_data:
            parent_id = str(nested.get(id_field))
            if parent_id in parent_map:
                parent_map[parent_id][nested_field].append(nested)

    return list(parent_map.values())


def remove_metadata_fields(data):
    """
    Recursively remove metadata fields from data structure.
    Removes: restored_by, restored_from, restored_at, _id

    Args:
        data: Dict or List to clean

    Returns:
        Cleaned data (modifies in place)
    """
    metadata_fields = ["restored_by", "restored_from", "restored_at", "_id"]

    if isinstance(data, list):
        for item in data:
            remove_metadata_fields(item)
    elif isinstance(data, dict):
        # Remove metadata from current level
        for field in metadata_fields:
            data.pop(field, None)
        # Recursively process nested structures
        for value in data.values():
            if isinstance(value, (dict, list)):
                remove_metadata_fields(value)

    return data


def fetch_and_merge_restored_data(db, entity_name, collection_name, id_field, original_data):
    """
    Fetch restored data, rebuild nested arrays, merge with original, and return.

    Args:
        db: MongoDB database instance
        entity_name: Entity name (e.g., "Policy MFA")
        collection_name: Collection name (e.g., "okta_policy_mfa")
        id_field: ID field for matching (e.g., "policy_id")
        original_data: Original data from main collections

    Returns:
        Merged data with restored changes applied
    """
    restored_collection_name = f"_{collection_name}"

    # Check if restored collection exists
    if restored_collection_name not in db.list_collection_names():
        logger.info(f"No restored collection found: {restored_collection_name}")
        return original_data

    logger.info(f"Found restored collection: {restored_collection_name}")

    # Rebuild restored data with nested arrays (handles both simple and nested entities)
    restored_data = rebuild_restored_data_with_nested_arrays(
        db, entity_name, collection_name, id_field
    )
    logger.info(f"Rebuilt {len(restored_data)} restored records")

    if not restored_data:
        logger.info("No restored data after rebuild")
        return original_data

    # Merge restored changes with original data
    merged_data = merge_restored_with_original(original_data, restored_data, id_field)
    logger.info(f"Merged {len(merged_data)} records with restored changes")

    return merged_data


def _merge_records(original, restored, id_field, metadata_fields):
    """Merge original and restored records by ID."""
    if not restored:
        return original
    if not original:
        return restored

    # Map restored items by ID
    restored_map = {
        str(item.get(id_field)): item
        for item in restored
        if item.get(id_field)
    }

    merged = []
    for orig_item in original:
        item_id = str(orig_item.get(id_field)) if orig_item.get(id_field) else None

        if item_id and item_id in restored_map:
            # Merge: overlay restored fields onto original
            merged_item = copy.deepcopy(orig_item)
            for key, value in restored_map[item_id].items():
                if key not in metadata_fields:
                    merged_item[key] = value
            merged.append(merged_item)
        else:
            merged.append(orig_item)

    return merged


def merge_restored_with_original(original_data, restored_data, id_field):
    """
    Merge restored data with original data.
    Handles both simple entities and nested arrays.
    """
    if not restored_data:
        return original_data
    if not original_data:
        return restored_data

    metadata_fields = {"restored_by", "restored_from", "restored_at", "_id"}

    # Map restored records by ID
    restored_map = {
        str(r.get(id_field)): r for r in restored_data if r.get(id_field)
    }

    merged_data = []
    for original_record in original_data:
        record_id = str(original_record.get(id_field)) if original_record.get(id_field) else None

        if record_id and record_id in restored_map:
            merged_record = copy.deepcopy(original_record)
            restored_record = restored_map[record_id]

            # Overlay restored fields
            for key, value in restored_record.items():
                if key in metadata_fields:
                    continue

                # Handle nested arrays
                if isinstance(value, list) and key in NESTED_FIELD_ID_MAPPING:
                    nested_id_field = NESTED_FIELD_ID_MAPPING[key].get("child_id_field", "id")
                    merged_record[key] = _merge_records(
                        merged_record.get(key, []), value, nested_id_field, metadata_fields
                    )
                else:
                    merged_record[key] = value

            merged_data.append(merged_record)
        else:
            merged_data.append(original_record)

    return merged_data
