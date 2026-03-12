import logging
import re
from datetime import datetime

from core.utils.collection_mapping import (ENTITY_ID_MAPPING,
                                           RESOURCE_COLLECTION_MAP)
from core.utils.nested_mapping import (ENTITIES_WITH_BUILDERS,
                                       NESTED_FIELD_COLLECTIONS,
                                       NESTED_FIELD_ID_MAPPING)
from deepdiff import DeepDiff
from django.conf import settings

logger = logging.getLogger(__name__)


def extract_time(db_name):
    """Extract time from database name."""
    if not db_name:
        return None

    pattern = r"(\d{4}-\d{2}-\d{2}T\d{4})"
    match = re.search(pattern, db_name)
    if match:
        return match.group(1)
    return None


def parse_input_date(date_str):
    """
    Parse a user-supplied date string into a datetime object.

    Accepts:
        - DD-MM-YY   (e.g. "09-08-25")
        - DD-MM-YYYY (e.g. "09-08-2025")

    Returns:
        datetime object on success, None on failure.
    """
    for fmt in ("%d-%m-%y", "%d-%m-%Y"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def _extract_time_display(time_part):
    """Convert compact time string to HH:MM. e.g. '0357' → '03:57'."""
    if len(time_part) == 4 and time_part.isdigit():
        return f"{time_part[:2]}:{time_part[2:]}"
    return time_part


def _format_date_display(date_part):
    """Convert YYYY-MM-DD to DD-MM-YYYY. e.g. '2026-03-10' → '10-03-2026'."""
    try:
        y, m, d = date_part.split("-")
        return f"{d}-{m}-{y}"
    except ValueError:
        return date_part


def resolve_db_name(date_str, time_str):
    """
    Reconstruct a MongoDB database name from date and time.

    Args:
        date_str: YYYY-MM-DD  (e.g. "2026-03-10")
        time_str: HH:MM       (e.g. "03:57")

    Returns:
        "bridgesec_2026-03-10T0357"
    """
    time_compact = time_str.replace(":", "")  # "03:57" → "0357"
    return f"{settings.MONGO_DB_NAME}_{date_str}T{time_compact}"


def list_databases_for_date(mongo_client, date_str, page=1, page_size=20):
    """
    Return paginated snapshots for a given date.
    """
    parsed = parse_input_date(date_str)
    if parsed is None:
        raise ValueError(
            f"Cannot parse date '{date_str}'. Use DD-MM-YY or DD-MM-YYYY."
        )

    iso_date = parsed.strftime("%Y-%m-%d")
    date_prefix = f"{settings.MONGO_DB_NAME}_{iso_date}"
    display_date = _format_date_display(iso_date)

    logger.info("Listing databases for date",
                extra={"operation": "list_databases_for_date", "iso_date": iso_date})

    all_items = []
    for db in sorted(db for db in mongo_client.list_database_names() if db.startswith(date_prefix)):
        stripped = db[len(f"{settings.MONGO_DB_NAME}_"):]
        if "T" not in stripped:
            continue
        _, time_part = stripped.split("T", 1)
        all_items.append({"time": _extract_time_display(time_part), "db_name": db})

    total = len(all_items)
    start = (page - 1) * page_size
    end = start + page_size

    return {
        "dates": [
            {
                "date": display_date,
                "snapshot_count": total,
                "snapshots": all_items[start:end],
            }
        ]
    }


def get_db_map(mongo_client):
    """
    Return all dates with all their snapshots grouped by date.

    Returns:
        {
          "10-03-2026": {
            "snapshot_count": 3,
            "snapshots": [
              {"time": "00:00", "db_name": "bridgesec_2026-03-10T0000"},
              {"time": "03:57", "db_name": "bridgesec_2026-03-10T0357"},
              {"time": "16:17", "db_name": "bridgesec_2026-03-10T1617"},
            ]
          },
          "09-03-2026": {
            "snapshot_count": 1,
            "snapshots": [
              {"time": "12:00", "db_name": "bridgesec_2026-03-09T1200"}
            ]
          }
        }
    """
    prefix = f"{settings.MONGO_DB_NAME}_"
    logger.info("Building full db map", extra={"operation": "get_db_map"})

    grouped = {}
    for db in sorted(mongo_client.list_database_names()):
        if not db.startswith(prefix):
            continue
        stripped = db[len(prefix):]
        if "T" not in stripped:
            continue
        date_part, time_part = stripped.split("T", 1)
        display_date = _format_date_display(date_part)
        if display_date not in grouped:
            grouped[display_date] = []
        grouped[display_date].append({"time": _extract_time_display(time_part), "db_name": db})

    return {
        "dates": [
            {
                "date": date,
                "snapshot_count": len(snaps),
                "snapshots": snaps
            }
            for date, snaps in grouped.items()
        ]
    }


def get_collection_name(entity_name):
    """Get collection name for a given entity type."""
    logger.info("Extracting collection name for the given entity from mappings",extra={"operation":'Get Collection Name'})
    for entity_type, sub_entities in RESOURCE_COLLECTION_MAP.items():
        for entry in sub_entities:
            for display_name, collection_name in entry.items():
                if display_name == entity_name:
                    return collection_name
    return None


def get_latest_db(mongo_client, date_str):
    """Get the latest database for a given date."""
    try:
        logger.info("Finding Latest DB for given date",extra={"operation":'Get Latest Db'})
        datetime.strptime(date_str, "%Y-%m-%d")
        date_prefix = f"{settings.MONGO_DB_NAME}_{date_str}"

        all_dbs = mongo_client.list_database_names()
        matching_dbs = [db for db in all_dbs if db.startswith(date_prefix)]

        if not matching_dbs:
            return None

        # Sort by time and return latest
        db_dict = {extract_time(db): db for db in matching_dbs if extract_time(db)}
        if db_dict:
            latest_time = max(db_dict.keys())
            return db_dict[latest_time]

        return None
    except ValueError:
        logger.info("Couldn't Find Latest DB for given date",extra={"operation":'Get Latest Db'})
        return None


def _build_item_dict(items, id_field):
    """Convert list to dict keyed by ID field."""
    return {
        str(item[id_field]): item
        for item in items
        if item.get(id_field)
    }


def get_ordered_unique_ids(old_array, new_array, id_field):
    """
    Get ordered unique IDs from both old and new arrays.
    Preserves order and skips duplicates.
    """
    seen = set()
    all_ids = []

    for array in (old_array, new_array):
        for item in array:
            item_id = str(item.get(id_field))
            if item_id and item_id not in seen:
                seen.add(item_id)
                all_ids.append(item_id)

    return all_ids


def _build_aligned_arrays(all_ids, old_items, new_items):
    """Build aligned arrays with {} placeholders where items don't exist."""
    return (
        [old_items.get(i, {}) for i in all_ids],
        [new_items.get(i, {}) for i in all_ids],
    )


def _compute_id_differences(old_items, new_items):
    """Compute added, removed, and common IDs."""
    old_ids, new_ids = set(old_items), set(new_items)
    return new_ids - old_ids, old_ids - new_ids, old_ids & new_ids


def _get_modified_items(common_ids, old_items, new_items, id_field):
    """Find modified items by comparing common IDs."""
    modified = []
    for item_id in common_ids:
        diff = DeepDiff(old_items[item_id], new_items[item_id], ignore_order=True)
        if diff:
            modified.append({id_field: item_id, "diff": diff.to_dict()})
    return modified


def compare_nested_arrays(old_doc, new_doc, entity_name):
    """Compare nested arrays in old and new documents for builder entities."""
    nested_mappings = NESTED_FIELD_COLLECTIONS.get(entity_name, {})
    if not nested_mappings:
        return {}, old_doc, new_doc

    nested_diffs = {}
    aligned_old, aligned_new = dict(old_doc or {}), dict(new_doc or {})

    for nested_field, _ in nested_mappings.items():
        old_array = (old_doc or {}).get(nested_field, [])
        new_array = (new_doc or {}).get(nested_field, [])

        id_field = NESTED_FIELD_ID_MAPPING.get(nested_field, {}).get("child_id_field")
        if not id_field:
            if old_array != new_array:
                nested_diffs[nested_field] = {
                    "type": "array_changed",
                    "old_count": len(old_array),
                    "new_count": len(new_array),
                }
            continue

        old_items = _build_item_dict(old_array, id_field)
        new_items = _build_item_dict(new_array, id_field)
        all_ids = get_ordered_unique_ids(old_array, new_array, id_field)

        aligned_old[nested_field], aligned_new[nested_field] = _build_aligned_arrays(all_ids, old_items, new_items)

        _, _, common_ids = _compute_id_differences(old_items, new_items)
        modified_items = _get_modified_items(common_ids, old_items, new_items, id_field)

        if modified_items:
            nested_diffs[nested_field] = modified_items

    return nested_diffs, aligned_old, aligned_new


def _get_main_doc_diff(old_doc, new_doc, entity_name=None):
    """Compute DeepDiff for main document fields (excluding nested for builder entities)."""
    if not old_doc or not new_doc:
        return None

    if entity_name in ENTITIES_WITH_BUILDERS:
        nested_fields = set(NESTED_FIELD_COLLECTIONS.get(entity_name, {}))
        old_filtered = {k: v for k, v in old_doc.items() if k not in nested_fields}
        new_filtered = {k: v for k, v in new_doc.items() if k not in nested_fields}
        return DeepDiff(old_filtered, new_filtered, ignore_order=True)

    return DeepDiff(old_doc, new_doc, ignore_order=True)


def get_collection_diff(old_docs, new_docs, id_field, entity_name=None, date1=None, date2=None):
    """Compare two lists of documents and return detailed diff."""
    old_map = {str(doc[id_field]): doc for doc in old_docs if id_field in doc}
    new_map = {str(doc[id_field]): doc for doc in new_docs if id_field in doc}

    is_builder = entity_name in ENTITIES_WITH_BUILDERS if entity_name else False
    all_ids = set(old_map) | set(new_map)

    changed = []
    comparison_pairs = []

    for doc_id in all_ids:
        old_doc, new_doc = old_map.get(doc_id), new_map.get(doc_id)

        if is_builder and (old_doc or new_doc):
            nested_diff, aligned_old, aligned_new = compare_nested_arrays(old_doc, new_doc, entity_name)
            comparison_pairs.append([aligned_old or {}, aligned_new or {}])

            main_diff = _get_main_doc_diff(old_doc, new_doc, entity_name)
            if main_diff or nested_diff:
                entry = {id_field: doc_id, "diff": main_diff.to_dict() if main_diff else {}}
                if nested_diff:
                    entry["nested_changes"] = nested_diff
                changed.append(entry)
        else:
            comparison_pairs.append([old_doc or {}, new_doc or {}])
            main_diff = _get_main_doc_diff(old_doc, new_doc, entity_name)
            if main_diff:
                changed.append({id_field: doc_id, "diff": main_diff.to_dict()})

    return {
        "comparison": comparison_pairs,
        "changed": changed,
        "summary": {
            "total_changed": len(changed),
            "total_records": len(comparison_pairs),
        },
        "metadata": {
            "entity_name": entity_name or "Unknown",
            "date1": date1 or "",
            "date2": date2 or "",
            "id_field": id_field,
        },
    }
