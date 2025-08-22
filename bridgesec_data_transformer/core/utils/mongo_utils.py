from datetime import datetime
from mongoengine import connect, get_connection
from django.conf import settings
import logging

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
