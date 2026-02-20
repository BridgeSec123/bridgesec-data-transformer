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

    logger.info(f"Stored {len(records)} records in '{collection_name}' for entity {entity_name}",extra={"operation":"Stores Data Without Restore Metadata"})


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
            logger.info(f"Detected nested collection {collection_name}, using child_id_field: {id_field}",extra={"operation":"Stores Data With Restore Metadata"})
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

        logger.info(f"Upserted {upsert_count} records to {restored_collection_name}",extra={"operation":"Stores Data With Restore Metadata"})
    else:
        # Fallback: replace all data (dangerous - deletes existing)
        logger.warning(f"No ID field defined for {entity_name}, using replace_all strategy",extra={"operation":"Stores Data With Restore Metadata"})

        # Add metadata to all records
        for doc in data:
            doc["restored_by"] = restored_by
            doc["restored_from"] = source_db_name
            doc["restored_at"] = restored_at
            doc.pop("_id", None)

        # Delete existing and insert new
        delete_result = restored_collection.delete_many({})
        logger.info(f"Deleted {delete_result.deleted_count} existing records from {restored_collection_name}",extra={"operation":"Stores Data With Restore Metadata"})

        if data:
            restored_collection.insert_many(data)
            logger.info(f"Inserted {len(data)} new records into {restored_collection_name}",extra={"operation":"Stores Data With Restore Metadata"})


def store_restored_data_with_metadata(db, entity_name, collection_name, modified_data, restored_by, source_db_name):
    """
    Universal function to store restored data.
    Handles BOTH simple entities AND entities with nested data (builders).
    """
    logger.info(f"Storing {len(modified_data)} records for {entity_name}",extra={"operation":"Universal Restore Data Storage"})

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

    logger.info(f"Storing created data for {entity_name}: {len(created_data)} records",extra={"operation":"Store New Data Without Metadata"})

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
                                                     
def store_deleted_data_with_metadata(db, entity_name, collection_name, deleted_data, deleted_by, source_db_name, cascade_parent_id=None, operation_type="deletion_pending"):
    """
    Store deleted data with deletion metadata.

    Args:
        db: MongoDB database instance (today's DB)
        entity_name: Entity name (e.g., "Policy MFA")
        collection_name: Collection name (e.g., "okta_policy_mfa")
        deleted_data: Complete records to mark as deleted
        deleted_by: Username who performed deletion
        source_db_name: Source database name
        cascade_parent_id: Parent ID if this is a cascaded deletion
        operation_type: Operation status - "deletion_pending" (before Terraform) or "deleted" (after Terraform success)

    Returns:
        Stored data
    """
    logger.info(f"Storing {len(deleted_data)} deleted records for {entity_name} with operation_type={operation_type}",extra={"operation":"Store Del Data With Metadata"})

    # Prepare metadata
    deleted_at = datetime.now().strftime("%H:%M:%S")
    deleted_collection_name = f"_{collection_name}"
    deleted_collection = db[deleted_collection_name]

    # Get ID field for upsert
    nested_mapping = NESTED_FIELD_COLLECTIONS.get(entity_name, {})
    id_field = None

    # Find if this collection is a nested collection
    for nested_field, nested_collection_name in nested_mapping.items():
        if nested_collection_name == collection_name:
            id_field = NESTED_FIELD_ID_MAPPING.get(nested_field, {}).get("child_id_field")
            logger.info(f"Detected nested collection {collection_name}, using child_id_field: {id_field}",extra={"operation":"Store Deletion Data With Metadata"})
            break

    # If not a nested collection, use the entity's ID field
    if not id_field:
        id_field = ENTITY_ID_MAPPING.get(entity_name)

    if not id_field:
        logger.error(f"No ID field defined for {entity_name}, cannot store deleted records",extra={"operation":"Store Deletion Data With Metadata"})
        return deleted_data

    # Store each deleted record with metadata
    upsert_count = 0
    for doc in deleted_data:
        doc_copy = copy.deepcopy(doc)

        # Add deletion metadata
        doc_copy["operation_type"] = operation_type  # "deletion_pending" before Terraform, "deleted" after success
        doc_copy["deleted_by"] = deleted_by
        doc_copy["deleted_from"] = source_db_name
        doc_copy["deleted_at"] = deleted_at
        if cascade_parent_id:
            doc_copy["cascade_parent_id"] = cascade_parent_id
        doc_copy.pop("_id", None)

        id_value = doc_copy.get(id_field)
        if id_value:
            # Upsert: update if exists, insert if not
            deleted_collection.replace_one(
                {id_field: id_value},
                doc_copy,
                upsert=True
            )
            upsert_count += 1
        else:
            logger.warning(f"Document missing {id_field} field, skipping",extra={"operation":"Store Deletion Data With Metadata"})

    logger.info(f"Upserted {upsert_count} deleted records to {deleted_collection_name}",extra={"operation":"Store Deletion Data With Metadata"})
    return deleted_data


def update_deletion_status(db, entity_name, collection_name, deleted_ids, new_status, terraform_error=None):
    """
    Update deletion status after Terraform operation completes.

    Args:
        db: MongoDB database instance (today's DB)
        entity_name: Entity name (e.g., "Policy MFA")
        collection_name: Collection name (e.g., "okta_policy_mfa")
        deleted_ids: List of IDs that were attempted to be deleted
        new_status: "deleted" (success) or "deletion_failed" (failure)
        terraform_error: Error message from Terraform (if failed)

    Returns:
        Number of records updated
    """
    logger.info(f"Updating deletion status to '{new_status}' for {len(deleted_ids)} records in {collection_name}",extra={"operation":"Update Deletion Status"})

    deleted_collection_name = f"_{collection_name}"
    deleted_collection = db[deleted_collection_name]

    # Get ID field
    id_field = ENTITY_ID_MAPPING.get(entity_name)
    if not id_field:
        logger.error(f"No ID field defined for {entity_name}, cannot update deletion status",extra={"operation":"Update Deletion Status"})
        return 0

    # Update each deleted record
    update_count = 0
    for deleted_id in deleted_ids:
        update_data = {
            "$set": {
                "operation_type": new_status,
                "status_updated_at": datetime.now().strftime("%H:%M:%S")
            }
        }

        # Add error details if deletion failed
        if terraform_error:
            update_data["$set"]["terraform_error"] = terraform_error

        result = deleted_collection.update_one(
            {id_field: deleted_id, "operation_type": "deletion_pending"},
            update_data
        )

        if result.modified_count > 0:
            update_count += 1

    logger.info(f"Updated {update_count} records to status '{new_status}' in {deleted_collection_name}",extra={"operation":"Update Deletion Status"})
    return update_count


def filter_deleted_records_from_state(merged_data, deleted_ids, id_field):
    """
    Remove deleted records from complete state before sending to Terraform.

    Args:
        merged_data: Complete merged data (original + restored)
        deleted_ids: List of IDs to remove
        id_field: ID field name for matching

    Returns:
        Filtered data without deleted records
    """
    if not deleted_ids:
        return merged_data

    deleted_ids_set = set(str(id_val) for id_val in deleted_ids if id_val)

    filtered_data = [
        record for record in merged_data
        if str(record.get(id_field)) not in deleted_ids_set
    ]

    logger.info(f"Filtered {len(merged_data) - len(filtered_data)} deleted records from state",extra={"operation":"Filter Deletion Data From State"})
    return filtered_data


def handle_nested_deletion(db, entity_name, deleted_parent_records, deleted_by, source_db_name):
    """
    Handle cascade deletion for entities with nested data.

    Args:
        db: MongoDB database instance (today's DB)
        entity_name: Entity name
        deleted_parent_records: Parent records being deleted
        deleted_by: Username who performed deletion
        source_db_name: Source database name

    Returns:
        Tuple of (all_deleted_ids, cascade_info)
        - all_deleted_ids: List of all deleted IDs (parent + children)
        - cascade_info: Dict with cascade details
    """
    # Check if entity has nested data
    nested_mapping = NESTED_FIELD_COLLECTIONS.get(entity_name)

    if not nested_mapping:
        # No nested data, return parent IDs only
        parent_id_field = ENTITY_ID_MAPPING.get(entity_name)
        parent_ids = [str(record.get(parent_id_field)) for record in deleted_parent_records if record.get(parent_id_field)]
        return parent_ids, {}

    # Entity has nested data - cascade deletion
    parent_id_field = ENTITY_ID_MAPPING.get(entity_name)
    parent_ids = [str(record.get(parent_id_field)) for record in deleted_parent_records if record.get(parent_id_field)]

    cascade_info = {
        "parent_count": len(parent_ids),
        "parent_ids": parent_ids,
        "nested_deletions": {}
    }

    all_deleted_ids = list(parent_ids)

    # Process each nested collection
    for nested_field, nested_collection_name in nested_mapping.items():
        nested_coll = f"_{nested_collection_name}"

        # Get nested ID mapping
        nested_id_config = NESTED_FIELD_ID_MAPPING.get(nested_field, {})
        child_id_field = nested_id_config.get("child_id_field", "id")
        parent_id_field_in_nested = nested_id_config.get("parent_id_field", parent_id_field)

        # Find all child records for deleted parents
        if nested_coll not in db.list_collection_names():
            logger.info(f"No nested collection found: {nested_coll}",extra={"operation":"Handle Nested Deletion"})
            continue

        # Query for children of deleted parents
        # Note: We check both the nested collection and original nested arrays
        child_records_to_delete = []

        # Extract nested arrays from parent records
        for parent_record in deleted_parent_records:
            nested_array = parent_record.get(nested_field, [])
            if nested_array:
                child_records_to_delete.extend(nested_array)

        if child_records_to_delete:
            # Store child records as deleted with cascade metadata
            child_ids = [str(child.get(child_id_field)) for child in child_records_to_delete if child.get(child_id_field)]

            # Store with cascade parent ID
            for parent_id in parent_ids:
                # Filter children belonging to this parent
                parent_children = [
                    child for child in child_records_to_delete
                    if str(child.get(parent_id_field_in_nested)) == parent_id
                ]

                if parent_children:
                    store_deleted_data_with_metadata(
                        db, entity_name, nested_collection_name,
                        parent_children, deleted_by, source_db_name,
                        cascade_parent_id=parent_id
                    )

            cascade_info["nested_deletions"][nested_field] = {
                "collection": nested_collection_name,
                "count": len(child_ids),
                "ids": child_ids
            }

            all_deleted_ids.extend(child_ids)

            logger.info(f"Cascade deleted {len(child_ids)} records from {nested_collection_name}",extra={"operation":"Handle Nested Deletion"})

    return all_deleted_ids, cascade_info


def validate_deletion_safety(source_db, entity_name, collection_name, deleted_records):
    """
    Validate deletion safety before processing.

    Args:
        source_db: Source MongoDB database instance
        entity_name: Entity name
        collection_name: Collection name
        deleted_records: Records to delete

    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    id_field = ENTITY_ID_MAPPING.get(entity_name)

    if not id_field:
        errors.append(f"No ID field configured for entity '{entity_name}'")
        return errors

    # Validate each record
    for i, record in enumerate(deleted_records):
        record_id = record.get(id_field)

        # Check ID field is present
        if not record_id:
            errors.append(f"Record at index {i} missing required ID field '{id_field}'")
            continue

        # Check resource exists in source DB
        source_collection = source_db[collection_name]
        existing_record = source_collection.find_one({id_field: record_id}, {"_id": 0})

        if not existing_record:
            errors.append(f"Record with {id_field}='{record_id}' not found in source database")

    return errors


def extract_terraform_target_params(collection_name, data_to_send, operation_type=None, target_ids=None):
    """
    Extract target field IDs and build parameters for Terraform API.

    Args:
        collection_name: Collection name
        data_to_send: Data being sent to Terraform
        operation_type: Operation type ("delete", None for restore/create)
        target_ids: List of target IDs for deletion

    Returns:
        Dict of parameters for Terraform API
    """
    params = {"collection_name": collection_name}

    # Add deletion parameters if applicable
    if operation_type == "delete" and target_ids:
        params["target_id"] = ",".join(str(id_val) for id_val in target_ids if id_val)
        params["operation"] = "delete"
        logger.info(f"Added deletion params: target_id={params['target_id']}",extra={"operation":"Extract TF Target Params"})

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
    Filters out records with operation_type="deleted".
    """
    nested_mapping = NESTED_FIELD_COLLECTIONS.get(entity_name)

    # Simple entity - fetch and return latest versions
    if not nested_mapping:
        coll_name = f"_{collection_name}"
        if coll_name in db.list_collection_names():
            all_data = list(db[coll_name].find({}, {"_id": 0}))
            latest_data = _get_latest_records_by_id(all_data, id_field)
            # Filter out deleted, deletion_pending, and deletion_failed records
            latest_data = [
                record for record in latest_data
                if record.get("operation_type") not in ["deleted", "deletion_pending", "deletion_failed"]
            ]
            return latest_data
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

    # Filter out deleted, deletion_pending, and deletion_failed parents
    parent_data = [
        record for record in parent_data
        if record.get("operation_type") not in ["deleted", "deletion_pending", "deletion_failed"]
    ]

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

        # Get nested ID field and parent ID field from mapping
        nested_id_field = NESTED_FIELD_ID_MAPPING.get(nested_field, {}).get("child_id_field", "id")
        parent_id_field = NESTED_FIELD_ID_MAPPING.get(nested_field, {}).get("parent_id_field", id_field)

        nested_data = _get_latest_records_by_id(
            list(db[nested_coll].find({}, {"_id": 0})), nested_id_field
        )

        # Filter out deleted, deletion_pending, and deletion_failed nested records
        nested_data = [
            record for record in nested_data
            if record.get("operation_type") not in ["deleted", "deletion_pending", "deletion_failed"]
        ]

        # Attach to parents using the correct parent_id_field from nested record
        for nested in nested_data:
            # Use parent_id_field to get the parent ID from nested record
            parent_id_value = str(nested.get(parent_id_field))

            # Match against parent's actual ID field value
            for parent_key, parent_record in parent_map.items():
                if parent_key == parent_id_value:
                    parent_record[nested_field].append(nested)
                    break

    return list(parent_map.values())


def remove_metadata_fields(data):
    """
    Recursively remove metadata fields from data structure.
    Removes all internal tracking fields before sending to Terraform.

    Removes:
        - restored_by, restored_from, restored_at (restore metadata)
        - deleted_by, deleted_from, deleted_at (deletion metadata)
        - cascade_parent_id (cascade deletion tracking)
        - terraform_error (error details from failed operations)
        - status_updated_at (status update timestamp)
        - operation_type (create/restore/delete indicator)
        - created_at, updated_at (timestamp fields)
        - unique_id (tracking ID for created resources)
        - _id (MongoDB ID)

    Args:
        data: Dict or List to clean

    Returns:
        Cleaned data (modifies in place)
    """
    metadata_fields = [
        "restored_by",
        "restored_from",
        "restored_at",
        "deleted_by",
        "deleted_from",
        "deleted_at",
        "cascade_parent_id",
        "terraform_error",
        "status_updated_at",
        "operation_type",
        "created_at",
        "updated_at",
        "unique_id",
        "_id"
    ]

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
        logger.info(f"No restored collection found: {restored_collection_name}",extra={"operation":'Fetch Merge Restored Data'})
        return original_data

    logger.info(f"Found restored collection: {restored_collection_name}",extra={"operation":'Fetch Merge Restored Data'})

    # Rebuild restored data with nested arrays (handles both simple and nested entities)
    restored_data = rebuild_restored_data_with_nested_arrays(
        db, entity_name, collection_name, id_field
    )
    logger.info(f"Rebuilt {len(restored_data)} restored records",extra={"operation":'Fetch Merge Restored Data'})

    if not restored_data:
        logger.info("No restored data after rebuild")
        return original_data

    # Merge restored changes with original data
    merged_data = merge_restored_with_original(original_data, restored_data, id_field)
    logger.info(f"Merged {len(merged_data)} records with restored changes",extra={"operation":'Fetch Merge Restored Data'})

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
    merged_ids = set()

    # First pass: merge existing original items with restored changes
    for orig_item in original:
        item_id = str(orig_item.get(id_field)) if orig_item.get(id_field) else None

        if item_id and item_id in restored_map:
            # Merge: overlay restored fields onto original
            merged_item = copy.deepcopy(orig_item)
            for key, value in restored_map[item_id].items():
                if key not in metadata_fields:
                    merged_item[key] = value
            merged.append(merged_item)
            merged_ids.add(item_id)
        else:
            merged.append(orig_item)
            if item_id:
                merged_ids.add(item_id)

    # Second pass: add NEW items from restored that don't exist in original
    for item_id, restored_item in restored_map.items():
        if item_id not in merged_ids:
            # This is a new item, add it
            clean_item = copy.deepcopy(restored_item)
            # Remove metadata fields
            for field in metadata_fields:
                clean_item.pop(field, None)
            merged.append(clean_item)

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
