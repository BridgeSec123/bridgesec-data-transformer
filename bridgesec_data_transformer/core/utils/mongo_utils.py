from datetime import datetime
from mongoengine import connect, get_connection, disconnect_all
from django.conf import settings
import logging
import threading
import os
from core.utils.entity_mapping import clean_entity_data

logger = logging.getLogger(__name__)

# ── Lazy system MongoDB client ────────────────────────────────────────────────
# Resolved once on first use so the container starts without MONGO_URI in .env.
# Resolution order:
#   1. MONGO_URI in .env          — fast path, no Supabase call needed
#   2. First active tenant in Supabase with a mongo_uri configured
#   3. RuntimeError               — no MongoDB available anywhere
_system_client = None
_system_client_lock = threading.Lock()


def get_system_mongo_client():
    """
    Return the system-level MongoClient for control-plane collections
    (bulk_progress, pending_deletion_plans indexes, Celery result backend, etc.).
    Cached for the lifetime of the process — Supabase is queried at most once.
    """
    global _system_client
    if _system_client is not None:
        return _system_client

    with _system_client_lock:
        if _system_client is not None:
            return _system_client

        from pymongo import MongoClient

        # Fast path: MONGO_URI present in .env
        uri = getattr(settings, 'MONGO_URI', '') or ''
        if uri:
            _system_client = MongoClient(uri)
            logger.info("System MongoDB client initialised from MONGO_URI env var")
            return _system_client

        # Supabase path: fetch first active tenant that has a mongo_uri
        try:
            from core.utils.supabase_tenant import SupabaseTenant
            tenants, _ = SupabaseTenant.list_all(active_only=True, page=1, page_size=10)
            for t in tenants:
                if t.mongo_uri:
                    _system_client = MongoClient(t.mongo_uri)
                    logger.info(
                        f"System MongoDB client initialised from tenant '{t.name}' in Supabase"
                    )
                    return _system_client
        except Exception as e:
            logger.warning(f"Could not fetch system tenant from Supabase: {e}")

        raise RuntimeError(
            "No MongoDB URI available. Either set MONGO_URI in .env or ensure at least "
            "one active tenant with a mongo_uri exists in Supabase."
        )


# ── Process-local connection manager ─────────────────────────────────────────

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
        if not hasattr(self._local, 'connected_dbs'):
            self._local.connected_dbs = set()
        return self._local.connected_dbs

    @property
    def process_id(self):
        return os.getpid()

    def is_connected(self, db_name):
        return db_name in self.connected_dbs

    def mark_connected(self, db_name):
        self.connected_dbs.add(db_name)

    def reset(self):
        if hasattr(self._local, 'connected_dbs'):
            self._local.connected_dbs.clear()


# Global instance — each process gets its own via threading.local
_connection_manager = ProcessLocalConnectionManager()


def get_dynamic_db(prefix: str = None):
    """
    Generate a snapshot DB name for a bulk API request.
    Pass the tenant's mongo_db_prefix so the snapshot lands in the tenant's
    namespace (e.g. "hotbeans_2026-05-30T1430").
    Falls back to settings.MONGO_DB_NAME when prefix is None.
    """
    utc_now = datetime.now().strftime("%Y-%m-%dT%H%M")
    base = prefix if prefix else settings.MONGO_DB_NAME
    return f"{base}_{utc_now}"


def connect_to_mongo():
    """Legacy helper — no-op when MONGO_URI is not configured."""
    uri = getattr(settings, 'MONGO_URI', '') or ''
    if not uri:
        logger.info("connect_to_mongo() skipped — MONGO_URI not set, using lazy tenant client")
        return
    db_name = get_dynamic_db()
    connect(db=db_name, host=uri, alias=db_name)


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

    Pass the tenant's mongo_uri so MongoEngine connects to the correct cluster.
    When mongo_uri is None, falls back to the system client URI (from .env or Supabase).
    """
    if not mongo_uri:
        mongo_uri = getattr(settings, 'MONGO_URI', '') or None

    if not mongo_uri:
        # Resolve from system client so we never use an empty URI
        try:
            client = get_system_mongo_client()
            # Extract URI from the client's topology description
            mongo_uri = client.HOST if hasattr(client, 'HOST') else None
        except Exception:
            pass

    if not mongo_uri:
        raise RuntimeError(
            f"Cannot connect to MongoDB database '{db_name}': no URI available. "
            "Set MONGO_URI in .env or configure mongo_uri on the tenant in Supabase."
        )

    global _connection_manager
    pid = _connection_manager.process_id

    # Ensure 'default' connection exists for this process
    if not _connection_manager.is_connected("default"):
        try:
            get_connection(alias="default")
            _connection_manager.mark_connected("default")
        except Exception:
            logger.info(f"[PID {pid}] Establishing default MongoDB connection")
            connect(db=db_name, host=mongo_uri, alias="default")
            _connection_manager.mark_connected("default")

    # Ensure specific database connection exists for this process
    if not _connection_manager.is_connected(db_name):
        logger.info(f"[PID {pid}] Connecting to MongoDB database: {db_name}")
        connect(db=db_name, host=mongo_uri, alias=db_name)
        _connection_manager.mark_connected(db_name)


def store_entity_incrementally(entity_name, entity_data, viewset_instance, db_name):
    """Clean and store a single entity's data immediately."""
    if not entity_data:
        logger.warning(f"No data to store for {entity_name}")
        return 0

    cleaned_data = clean_entity_data(entity_name, entity_data)
    viewset_instance.store_data(cleaned_data, db_name)
    logger.info(f"[INCREMENTAL STORAGE] Stored {len(cleaned_data)} records for '{entity_name}' in DB: {db_name}")
    return len(cleaned_data)
