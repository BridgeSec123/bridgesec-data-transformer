from datetime import datetime
from mongoengine import connect, get_connection
from django.conf import settings
import logging
from core.utils.entity_mapping import clean_entity_data

logger = logging.getLogger(__name__)


def get_dynamic_db():
    """
    Generate a new database name for each bulk API request.
    Ensures all entities (users, groups, etc.) are stored in the same DB within a single request.
    """
    utc_now = datetime.now().strftime("%Y-%m-%dT%H%M")
    return f"{settings.MONGO_DB_NAME}_{utc_now}"

def connect_to_mongo():
    """Establish a connection to the dynamically named MongoDB database."""
    db_name = get_dynamic_db()
    connect(db=db_name, host=settings.MONGO_URI, alias=db_name)

# Track connected databases globally
CONNECTED_DBS = set()

def ensure_mongo_connection(db_name):
    """ 
    Ensure a connection to the given MongoDB database dynamically.
    """ 
    global CONNECTED_DBS

    # # 🔹 First, ensure a 'default' connection is set up
    if "default" not in CONNECTED_DBS:
        try:
            logger.info(f"Establishing default MongoDB connection to 1 {db_name}")
            get_connection(alias="default")  # Check if it exists
        except Exception:
            logger.info(f"Establishing default MongoDB connection to {db_name}")
            connect(
                db=db_name, 
                host=settings.MONGO_URI, 
                alias="default"
            )
            CONNECTED_DBS.add("default")

    # 🔹 Now, ensure the specific database is connected
    if db_name not in CONNECTED_DBS:
        logger.info(f"Connecting to MongoDB database: {db_name}")
        connect(db=db_name, host=settings.MONGO_URI, alias=db_name)
        CONNECTED_DBS.add(db_name)


def store_entity_incrementally(entity_name, entity_data, viewset_instance, db_name):
    """
    Clean and store a single entity's data immediately.
    """
    if not entity_data:
        logger.warning(f"No data to store for {entity_name}")
        return 0

    # Clean the data
    cleaned_data = clean_entity_data(entity_name, entity_data)

    # Store in DB
    viewset_instance.store_data(cleaned_data, db_name)

    logger.info(f"[INCREMENTAL STORAGE] Stored {len(cleaned_data)} records for '{entity_name}' in DB: {db_name}")

    return len(cleaned_data)
