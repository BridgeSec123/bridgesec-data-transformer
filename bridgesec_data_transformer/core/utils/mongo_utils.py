from datetime import datetime
from mongoengine import connect, get_connection, disconnect_all
from django.conf import settings
import logging
import threading
import os
from core.utils.entity_mapping import clean_entity_data

logger = logging.getLogger(__name__)


class ProcessLocalConnectionManager:
    """
    Manages MongoDB connections on a per-process basis.
    Uses threading.local() to ensure each thread/process has isolated state.
    This is required for multiprocessing safety.
    """

    def __init__(self):
        self._local = threading.local()

    @property
    def connected_dbs(self):
        """Get the set of connected databases for this process."""
        if not hasattr(self._local, 'connected_dbs'):
            self._local.connected_dbs = set()
        return self._local.connected_dbs

    @property
    def process_id(self):
        """Get current process ID for logging."""
        return os.getpid()

    def is_connected(self, db_name):
        """Check if a database connection exists in this process."""
        return db_name in self.connected_dbs

    def mark_connected(self, db_name):
        """Mark a database as connected in this process."""
        self.connected_dbs.add(db_name)

    def reset(self):
        """Reset connection state for this process (used in worker initialization)."""
        if hasattr(self._local, 'connected_dbs'):
            self._local.connected_dbs.clear()


# Global instance - each process gets its own via threading.local
_connection_manager = ProcessLocalConnectionManager()


def get_dynamic_db(prefix: str = None):
    """
    Generate a snapshot DB name for a bulk API request.
    When multi-tenancy is enabled, pass the tenant's mongo_db_prefix so the
    snapshot lands in the tenant's namespace (e.g. "acme_okta_2026-05-06T1430").
    Falls back to the global MONGO_DB_NAME when prefix is None.
    """
    utc_now = datetime.now().strftime("%Y-%m-%dT%H%M")
    base = prefix if prefix else settings.MONGO_DB_NAME
    return f"{base}_{utc_now}"


def connect_to_mongo():
    """Establish a connection to the dynamically named MongoDB database."""
    db_name = get_dynamic_db()
    connect(db=db_name, host=settings.MONGO_URI, alias=db_name)


def reset_connections_for_process():
    """
    Reset MongoDB connections for the current process.
    MUST be called at the start of each worker process.
    """
    global _connection_manager
    try:
        disconnect_all()
    except Exception as e:
        logger.warning(f"[PID {os.getpid()}] Error disconnecting MongoDB: {e}")
    _connection_manager.reset()
    logger.info(f"[PID {os.getpid()}] MongoDB connections reset for worker process")


def ensure_mongo_connection(db_name, mongo_uri: str = None):
    """
    Ensure a connection to the given MongoDB database.
    Process-safe: each process maintains its own connection state.

    When multi-tenancy is enabled, pass the tenant's mongo_uri so MongoEngine
    connects to the correct cluster. Falls back to settings.MONGO_URI when None.
    """
    uri = mongo_uri if mongo_uri else settings.MONGO_URI
    global _connection_manager
    pid = _connection_manager.process_id

    # Ensure 'default' connection exists for this process
    if not _connection_manager.is_connected("default"):
        try:
            get_connection(alias="default")
            _connection_manager.mark_connected("default")
        except Exception:
            logger.info(f"[PID {pid}] Establishing default MongoDB connection to {db_name}")
            connect(db=db_name, host=uri, alias="default")
            _connection_manager.mark_connected("default")

    # Ensure specific database connection exists for this process
    if not _connection_manager.is_connected(db_name):
        logger.info(f"[PID {pid}] Connecting to MongoDB database: {db_name}")
        connect(db=db_name, host=uri, alias=db_name)
        _connection_manager.mark_connected(db_name)


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
