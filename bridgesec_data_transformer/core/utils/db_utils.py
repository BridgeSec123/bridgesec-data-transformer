import re
from datetime import datetime
from django.conf import settings
from core.utils.collection_mapping import RESOURCE_COLLECTION_MAP


def extract_time(db_name):
    """Extract time from database name."""
    if not db_name:
        return None

    pattern = r"(\d{4}-\d{2}-\d{2}T\d{4})"
    match = re.search(pattern, db_name)
    if match:
        return match.group(1)
    return None


def normalize_db_name(db_name):
    """Normalize database name for consistent formatting."""
    if not db_name:
        return None

    # Extract date and time parts
    time_part = extract_time(db_name)
    if time_part:
        return db_name.replace(time_part, time_part.replace(":", "-"))
    return db_name


def get_collection_name(entity_name):
    """Get collection name for a given entity type."""
    for entity_type, sub_entities in RESOURCE_COLLECTION_MAP.items():
        for entry in sub_entities:
            for display_name, collection_name in entry.items():
                if display_name == entity_name:
                    return collection_name
    return None


def get_latest_db(mongo_client, date_str):
    """Get the latest database for a given date."""
    try:
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
        return None


