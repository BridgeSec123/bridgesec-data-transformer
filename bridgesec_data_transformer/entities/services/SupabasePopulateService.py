"""
Supabase client for Terraform state storage and lock management.

This module provides a backend for storing Terraform state files in Supabase Storage
and managing state locks in Supabase PostgreSQL to prevent concurrent modifications.
"""
import os
import json
import logging
import tempfile
import time
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from supabase import create_client, Client
# from core.utils.collection_mapping import RESOURCE_COLLECTION_MAP
from core.utils.entity_mapping import ENTITY_TYPE_MAPPING,ENTITY_TARGET_PREFIX_MAP
from core.utils.serializer_registry import SERIALIZER_REGISTRY
from core.utils.model_registry import MODEL_REGISTRY
from core.utils.mapping_handlers import RULES_FIELDS,MAPPED_ENTITIES_HELPERS,ID_KEYS,ENTITY_UNIQUE_FIELDS,NONE_FIELD_LISTS
from core.utils.entity_mapping import ENTITY_IMPORT_MAPPING, EXCLUDED_OUTPUT_FIELDS
from core.utils.collection_mapping import RESOURCE_COLLECTION_MAP, NON_EDITABLE_FIELDS
from core.utils.constants import ENTITY_TARGET_FIELD_MAP, SINGLETON_RESOURCE_IDENTIFIERS
from core.utils.nested_mapping import NESTED_FIELD_COLLECTIONS, NESTED_FIELD_ID_MAPPING, ENTITIES_WITH_BUILDERS
from core.utils.module_mapping import get_module_name,get_terraform_api_for_entity
from core.utils.oktf_mappings import (
    ENTITY_FIELD_MAPPING,
    COLLECTION_STATE_MAP,
    GROUPED_ENTITIES,
    NESTED_ENTITY_CONFIG,
    NESTED_ENTITY_KEYS,
    ENTITY_DEPENDENCY_MAPPING,
    TERRAFORM_KEY_ALIASES,
)
logger = logging.getLogger(__name__)

# Module-level write-through cache: populated by put_state(), read by get_state().
# Eliminates Supabase CDN staleness in the immediate post-upload window (same process).
# Keys: entity_name, Values: most recently uploaded state JSON string.
_state_write_cache: dict = {}

# Max age (seconds) for the temp-file cross-process cache to be considered fresh.
_CACHE_TTL_SECONDS = 120


def _get_cache_file_path(entity_name: str) -> str:
    """Return path for the cross-process temp-file state cache."""
    safe_name = entity_name.replace("/", "_").replace("\\", "_")
    return os.path.join(tempfile.gettempdir(), f"tf_state_cache_{safe_name}.json")


def _write_cross_process_cache(entity_name: str, state_content: str) -> None:
    """Write state to temp file for cross-process cache sharing."""
    try:
        cache_path = _get_cache_file_path(entity_name)
        tmp_path = cache_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(state_content)
        os.replace(tmp_path, cache_path)  # atomic rename
        logger.info(
            f"[CACHE FILE SET] Wrote cross-process cache for {entity_name} "
            f"({len(state_content)} bytes) → {cache_path}",
            extra={"operation": "State Cache"}
        )
    except Exception as e:
        logger.warning(f"[CACHE FILE] Failed to write cross-process cache for {entity_name}: {e}")


def _read_cross_process_cache(entity_name: str) -> Optional[str]:
    """
    Read state from temp file if it exists and is younger than _CACHE_TTL_SECONDS.
    Returns None if no fresh cache is available.
    """
    try:
        cache_path = _get_cache_file_path(entity_name)
        if not os.path.exists(cache_path):
            return None
        age = time.time() - os.path.getmtime(cache_path)
        if age > _CACHE_TTL_SECONDS:
            logger.info(
                f"[CACHE FILE] Cross-process cache for {entity_name} is too old ({age:.1f}s), ignoring.",
                extra={"operation": "State Cache"}
            )
            return None
        with open(cache_path, "r", encoding="utf-8") as f:
            content = f.read()
        logger.info(
            f"[CACHE FILE HIT] Read cross-process cache for {entity_name} "
            f"({len(content)} bytes, age={age:.1f}s)",
            extra={"operation": "State Cache"}
        )
        return content
    except Exception as e:
        logger.warning(f"[CACHE FILE] Failed to read cross-process cache for {entity_name}: {e}")
        return None


class SupabaseStateBackend:
    """
    Supabase backend for Terraform state storage and locking.

    Provides:
    - State file storage in Supabase Storage bucket
    - State locking via PostgreSQL table with TTL
    - Automatic lock expiration and cleanup
    """

    def __init__(self):
        """Initialize Supabase client with environment credentials."""
        self.url = os.getenv('SUPABASE_URL')
        self.key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        self.bucket = os.getenv('SUPABASE_BUCKET_NAME', 'terraform-states')

        if not self.url or not self.key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in environment"
            )

        try:
            # Create Supabase client
            # Note: The "Storage endpoint URL should have a trailing slash" warning
            # is from the supabase-py library and doesn't affect functionality
            self.client: Client = create_client(self.url, self.key)
            logger.info(f"Supabase client initialized for bucket: {self.bucket}",extra={'operation':'Initialize Supabase'})
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise

    def _get_state_filename(self, entity_name: str) -> str:
        """
        Get the state file path for an entity.

        Args:
            entity_name: Entity name (e.g., 'okta_app_oauth')

        Returns:
            File path in format: '<entity_name>/terraform.tfstate'
            This creates a folder structure in Supabase Storage
        """
        # Sanitize entity name to prevent path traversal
        entity_name = entity_name.replace('\\', '').replace('..', '')
        # Use folder structure: okta_app_oauth/terraform.tfstate
        # This allows for organized storage and future backup files
        return f"{entity_name}/terraform.tfstate"

    def get_state(self, entity_name: str, use_cache: bool = True) -> Optional[str]:
        """
        Download state file from Supabase Storage.

        Checks the in-process write-through cache first (populated by put_state) to
        avoid serving stale content from the Supabase CDN in the immediate post-upload window.

        Args:
            entity_name: Entity name (e.g., 'okta_app_oauth')
            use_cache: If True (default), return cached state when available

        Returns:
            State file content as JSON string, or None if not found

        Raises:
            Exception: If download fails for reasons other than file not found
        """
        # 1. Check in-process cache (same process, zero-cost read)
        if use_cache and entity_name in _state_write_cache:
            cached = _state_write_cache[entity_name]
            logger.info(
                f"[CACHE HIT] Returning in-memory state for {entity_name} ({len(cached)} bytes)",
                extra={'operation': 'Download State File'}
            )
            return cached

        # 2. Check cross-process temp-file cache (different gunicorn worker uploaded it)
        if use_cache:
            cached = _read_cross_process_cache(entity_name)
            if cached:
                _state_write_cache[entity_name] = cached  # promote to in-process cache
                return cached

        filename = self._get_state_filename(entity_name)

        try:
            logger.info(f"Downloading state file: {filename} from bucket: {self.bucket}",extra={'operation':'Download State File'})

            # Download file from Supabase Storage (flat structure, no nested paths)
            response = self.client.storage.from_(self.bucket).download(filename)

            if response:
                content = response.decode('utf-8')
                logger.info(f"Successfully downloaded state file: {filename} ({len(content)} bytes)",extra={'operation':'Download State File'})
                # Populate both caches so future reads in any process are instant
                _state_write_cache[entity_name] = content
                _write_cross_process_cache(entity_name, content)
                return content
            else:
                logger.info(f"State file does not exist yet: {filename}",extra={'operation':'Download State File'})
                return None

        except Exception as e:
            # Check if it's a "not found" error (common with first-time access)
            error_str = str(e).lower()
            if 'not found' in error_str or '404' in error_str or '400' in error_str or 'object not found' in error_str:
                logger.info(f"State file does not exist yet: {filename}",extra={'operation':'Download State File'})
                return None
            else:
                logger.error(f"Error downloading state file {filename}: {e}",extra={'operation':'Download State File'})
                logger.error(f"Full error details: {type(e).__name__}: {str(e)}",extra={'operation':'Download State File'})
                raise

    def put_state(self, entity_name: str, state_content: str) -> bool:
        """
        Upload state file to Supabase Storage.

        Automatically creates a backup of existing state before overwriting.

        Args:
            entity_name: Entity name (e.g., 'okta_app_oauth')
            state_content: State file content as JSON string

        Returns:
            True if upload successful, False otherwise

        Raises:
            Exception: If upload fails
        """
        filename = self._get_state_filename(entity_name)

        try:
            logger.info(f"Uploading state file: {filename} to bucket: {self.bucket} ({len(state_content)} bytes)",extra={'operation':'Upload State File'})

            # Create backup of existing state before overwriting
            existing_state = self.get_state(entity_name)
            if existing_state:
                try:
                    self._create_backup(entity_name, existing_state)
                except Exception as backup_error:
                    # Log but don't fail if backup fails
                    logger.warning(f"Failed to create backup for {entity_name}: {backup_error}",extra={'operation':'Upload State File'})

            # Convert string to bytes
            content_bytes = state_content.encode('utf-8')

            # Upload or update file in Supabase Storage (folder structure)
            # cache-control: no-store prevents CDN from serving a stale cached copy
            # after upsert — without it, GET requests immediately after apply return
            # the old state because the CDN cache is not yet invalidated.
            response = self.client.storage.from_(self.bucket).upload(
                filename,
                content_bytes,
                file_options={"content-type": "application/json", "upsert": "true", "cache-control": "no-store"}
            )

            logger.info(f"Successfully uploaded state file: {filename}",extra={'operation':'Upload State File'})
            # Update both caches so get_state() immediately returns the new content
            # regardless of whether the caller is in the same process or a different worker.
            _state_write_cache[entity_name] = state_content
            _write_cross_process_cache(entity_name, state_content)
            logger.info(f"[CACHE SET] Cached new state for {entity_name} ({len(state_content)} bytes)",extra={'operation':'Upload State File'})
            return True

        except Exception as e:
            logger.error(f"Error uploading state file {filename}: {e}",extra={'operation':'Upload State File'})
            logger.error(f"Full error details: {type(e).__name__}: {str(e)}",extra={'operation':'Upload State File'})
            raise

    def _create_backup(self, entity_name: str, state_content: str) -> bool:
        """
        Create a timestamped backup of the state file.

        Args:
            entity_name: Entity name (e.g., 'okta_app_oauth')
            state_content: State file content to backup

        Returns:
            True if backup created successfully
        """
        from datetime import datetime

        # Create backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{entity_name}/terraform.tfstate.{timestamp}.backup"

        try:
            logger.info(f"Creating backup: {backup_filename}",extra={'operation':'Backup State File'})

            content_bytes = state_content.encode('utf-8')

            response = self.client.storage.from_(self.bucket).upload(
                backup_filename,
                content_bytes,
                file_options={"content-type": "application/json"}
            )

            logger.info(f"Backup created successfully: {backup_filename}",extra={'operation':'Backup State File'})
            return True

        except Exception as e:
            logger.error(f"Error creating backup {backup_filename}: {e}",extra={'operation':'Backup State File'})
            raise

    def delete_state(self, entity_name: str) -> bool:
        """
        Delete state file from Supabase Storage.

        Args:
            entity_name: Entity name (e.g., 'okta_app_oauth')

        Returns:
            True if deletion successful, False otherwise
        """
        filename = self._get_state_filename(entity_name)

        try:
            logger.info(f"Deleting state file: {filename} from bucket: {self.bucket}",extra={'operation':'Delete State File'})

            # Delete file from Supabase Storage (flat structure)
            response = self.client.storage.from_(self.bucket).remove([filename])

            logger.info(f"Successfully deleted state file: {filename}",extra={'operation':'Delete State File'})
            return True

        except Exception as e:
            logger.error(f"Error deleting state file {filename}: {e}")
            return False

    def acquire_lock(self, entity_name: str, lock_info: dict) -> Dict[str, Any]:
        """
        Acquire lock for entity in PostgreSQL.

        Args:
            entity_name: Entity name (e.g., 'okta_app_oauth')
            lock_info: Lock information dict with keys:
                - ID: Unique lock ID
                - Operation: Operation type (e.g., 'apply', 'plan')
                - Who: Who is requesting the lock
                - Version: Terraform version
                - Created: ISO timestamp

        Returns:
            Dict with:
                - success: bool - True if lock acquired
                - lock_id: str - Lock ID if successful
                - message: str - Status message
                - existing_lock: dict - Existing lock info if conflict
        """
        lock_id = lock_info.get('ID', '')
        locked_by = lock_info.get('Who', 'unknown')

        try:
            logger.info(f"Attempting to acquire lock for entity: {entity_name}, lock_id: {lock_id}",extra={'operation':'Acquire SupaBase Lock'})

            # Check if lock already exists
            existing = self.client.table('terraform_locks').select('*').eq('entity_name', entity_name).execute()

            if existing.data:
                existing_lock = existing.data[0]
                existing_lock_id = existing_lock.get('lock_id')
                expires_at = existing_lock.get('expires_at')

                # Parse expiration time
                try:
                    expires_dt = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                    now = datetime.now(expires_dt.tzinfo)

                    # Check if lock is expired
                    if expires_dt <= now:
                        logger.info(f"Existing lock expired, deleting: {entity_name}",extra={'operation':'Acquire SupaBase Lock'})
                        # Delete expired lock
                        self.client.table('terraform_locks').delete().eq('entity_name', entity_name).execute()
                    elif existing_lock_id == lock_id:
                        # Same lock ID - refresh the lock
                        logger.info(f"Refreshing existing lock: {entity_name}, lock_id: {lock_id}",extra={'operation':'Acquire SupaBase Lock'})
                        # Use UTC consistently — acquire() and all comparisons use UTC, so a
                        # naive local time here would mis-set expiry on non-UTC hosts.
                        new_expires = datetime.now(timezone.utc) + timedelta(minutes=15)
                        self.client.table('terraform_locks').update({
                            'expires_at': new_expires.isoformat()
                        }).eq('entity_name', entity_name).execute()

                        return {
                            'success': True,
                            'lock_id': lock_id,
                            'message': 'Lock refreshed'
                        }
                    else:
                        # Lock held by different process
                        logger.warning(f"Lock conflict for entity: {entity_name}, held by: {existing_lock.get('locked_by')}",extra={'operation':'Acquire SupaBase Lock'})
                        return {
                            'success': False,
                            'lock_id': None,
                            'message': f"Lock held by {existing_lock.get('locked_by')}",
                            'existing_lock': existing_lock
                        }
                except Exception as e:
                    logger.error(f"Error parsing lock expiration: {e}",extra={'operation':'Acquire SupaBase Lock'})
                    # If we can't parse expiration, treat as expired
                    self.client.table('terraform_locks').delete().eq('entity_name', entity_name).execute()

            # Acquire new lock
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

            lock_data = {
                'entity_name': entity_name,
                'lock_id': lock_id,
                'locked_by': locked_by,
                'locked_at': datetime.now(timezone.utc).isoformat(),
                'expires_at': expires_at.isoformat(),
                'info': lock_info
            }

            self.client.table('terraform_locks').insert(lock_data).execute()

            logger.info(f"Lock acquired successfully for entity: {entity_name}, lock_id: {lock_id}",extra={'operation':'Acquire SupaBase Lock'})
            return {
                'success': True,
                'lock_id': lock_id,
                'message': 'Lock acquired'
            }

        except Exception as e:
            logger.error(f"Error acquiring lock for entity {entity_name}: {e}",extra={'operation':'Acquire SupaBase Lock'})
            return {
                'success': False,
                'lock_id': None,
                'message': f"Error acquiring lock: {str(e)}"
            }

    def release_lock(self, entity_name: str, lock_id: str) -> bool:
        """
        Release lock for entity in PostgreSQL.

        Args:
            entity_name: Entity name (e.g., 'okta_app_oauth')
            lock_id: Lock ID to release

        Returns:
            True if lock released, False otherwise
        """
        try:
            logger.info(f"Releasing lock for entity: {entity_name}, lock_id: {lock_id}")

            # Delete lock only if lock_id matches
            result = self.client.table('terraform_locks').delete().eq(
                'entity_name', entity_name
            ).eq(
                'lock_id', lock_id
            ).execute()

            if result.data:
                logger.info(f"Lock released successfully for entity: {entity_name}",extra={'operation':'Release SupaBase Lock'})
                return True
            else:
                logger.warning(f"Lock not found or lock_id mismatch for entity: {entity_name}",extra={'operation':'Release SupaBase Lock'})
                return False

        except Exception as e:
            logger.error(f"Error releasing lock for entity {entity_name}: {e}",extra={'operation':'Release SupaBase Lock'})
            return False

    def check_lock(self, entity_name: str) -> Optional[Dict[str, Any]]:
        """
        Check if entity is locked.

        Args:
            entity_name: Entity name (e.g., 'okta_app_oauth')

        Returns:
            Lock info dict if locked, None if not locked
        """
        try:
            result = self.client.table('terraform_locks').select('*').eq('entity_name', entity_name).execute()

            if result.data:
                lock_info = result.data[0]

                # Check if expired
                expires_at = lock_info.get('expires_at')
                try:
                    expires_dt = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                    now = datetime.now(expires_dt.tzinfo)

                    if expires_dt <= now:
                        logger.info(f"Lock expired for entity: {entity_name}",extra={'operation':'Check SupaBase Lock'})
                        return None
                except Exception as e:
                    logger.error(f"Error parsing lock expiration: {e}",extra={'operation':'Check SupaBase Lock'})
                    return None

                return lock_info
            else:
                return None

        except Exception as e:
            logger.error(f"Error checking lock for entity {entity_name}: {e}",extra={'operation':'Check SupaBase Lock'})
            return None

    def cleanup_expired_locks(self) -> int:
        """
        Remove expired locks from PostgreSQL.

        Returns:
            Number of locks cleaned up
        """
        try:
            logger.info("Cleaning up expired locks...")

            # Get all locks
            result = self.client.table('terraform_locks').select('*').execute()

            cleaned = 0
            now = datetime.now(timezone.utc)

            for lock in result.data:
                entity_name = lock.get('entity_name')
                expires_at = lock.get('expires_at')

                try:
                    expires_dt = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                    if expires_dt.tzinfo is None:
                        expires_dt = expires_dt.replace(tzinfo=timezone.utc)

                    if expires_dt <= now:
                        # Delete expired lock
                        self.client.table('terraform_locks').delete().eq('entity_name', entity_name).execute()
                        logger.info(f"Cleaned up expired lock for entity: {entity_name}",extra={'operation':'Clean SupaBase Lock'})
                        cleaned += 1
                except Exception as e:
                    logger.error(f"Error parsing expiration for entity {entity_name}: {e}",extra={'operation':'Clean SupaBase Lock'})
                    continue

            logger.info(f"Cleanup complete. Removed {cleaned} expired lock(s)",extra={'operation':'Clean SupaBase Lock'})
            return cleaned

        except Exception as e:
            logger.error(f"Error cleaning up expired locks: {e}",extra={'operation':'Clean SupaBase Lock'})
            return 0

    def populate_terraform_registry(self):
        """
        Fully populate + update terraform_registry in ONE pass
        """

        try:
            records_to_upsert = []

            for category, entity_list in RESOURCE_COLLECTION_MAP.items():
                logger.info(f"[CATEGORY] Processing category: {category}")

                for entity_map in entity_list:
                    for entity_name, terraform_key in entity_map.items():

                        logger.debug(f"[ENTITY] Processing entity: {entity_name}")
                        # =========================
                        # MODEL REGISTRY
                        # =========================
                        model = MODEL_REGISTRY.get(entity_name)
                        if not model:
                            logger.warning(f"[SKIP] Model not found: {entity_name}")
                            continue

                        model_class = model.__name__
                        model_module_path = model.__module__

                        # =========================
                        # SERIALIZER REGISTRY
                        # =========================
                        serializer = SERIALIZER_REGISTRY.get(entity_name)

                        serializer_class = serializer.__name__ if serializer else ""
                        serializer_module_path = serializer.__module__ if serializer else ""

                        # =========================
                        # MODULE MAPPING
                        # =========================
                        module_name = get_module_name(entity_name)
                        base_api_path = get_terraform_api_for_entity(entity_name)

                        # =========================
                        # ID + RULES
                        # =========================
                        id_key = ID_KEYS.get(terraform_key, "")
                        rules_field = RULES_FIELDS.get(terraform_key, "")

                        # =========================
                        # SCALAR FIELDS
                        # =========================

                        # terraform_module_path (primary target address)
                        module_paths = ENTITY_TARGET_PREFIX_MAP.get(terraform_key, [])
                        terraform_module_path = module_paths[0] if module_paths else ""

                        # unique_key — precedence: MAPPED_ENTITIES_HELPERS (most complete/current)
                        # then mapping_handlers.ENTITY_UNIQUE_FIELDS.
                        unique_key = (
                            MAPPED_ENTITIES_HELPERS.get("entity_unique_fields", {}).get(terraform_key)
                            or ENTITY_UNIQUE_FIELDS.get(terraform_key)
                            or ""
                        )

                        # okta_endpoint
                        okta_config = ENTITY_TYPE_MAPPING.get(terraform_key) or {}
                        okta_endpoint = okta_config.get("okta_endpoint", "")

                        # import config (folded 1:1 from ENTITY_IMPORT_MAPPING)
                        imp = ENTITY_IMPORT_MAPPING.get(terraform_key) or {}

                        # singleton
                        is_singleton = terraform_key in SINGLETON_RESOURCE_IDENTIFIERS
                        singleton_identifier = SINGLETON_RESOURCE_IDENTIFIERS.get(terraform_key, "")

                        # aliases — alternate terraform_key spellings that resolve to this key
                        aliases = [
                            alias for alias, canonical in TERRAFORM_KEY_ALIASES.items()
                            if canonical == terraform_key
                        ]

                        # =========================
                        # FINAL RECORD
                        # =========================
                        record = {
                            "terraform_key": terraform_key,
                            "display_name": entity_name,
                            "category": category,

                            "model_class": model_class,
                            "model_module_path": model_module_path,

                            "serializer_class": serializer_class,
                            "serializer_module_path": serializer_module_path,

                            "module_key": module_name or "",
                            "base_api_path": base_api_path or "",
                            "entity_module": module_name or "",

                            "okta_endpoint": okta_endpoint,
                            "id_key": id_key,
                            "unique_key": unique_key,
                            "terraform_module_path": terraform_module_path,
                            "rules_field": rules_field,

                            # OkTfModules-only scalars
                            "wrapper_key": ENTITY_FIELD_MAPPING.get(terraform_key, ""),
                            "state_file_path": COLLECTION_STATE_MAP.get(terraform_key, ""),

                            # folded import config (1:1)
                            "import_address": imp.get("import_address", ""),
                            "okta_id_field": imp.get("okta_id_field", ""),
                            "terraform_key_field": imp.get("terraform_key_field", ""),
                            "import_id_format": imp.get("import_id_format", ""),
                            "terraform_key_format": imp.get("terraform_key_format", ""),

                            # flags
                            "singleton_entity": is_singleton,
                            "singleton_identifier": singleton_identifier,
                            "has_builders": entity_name in ENTITIES_WITH_BUILDERS,
                            "uses_composite_key": terraform_key in GROUPED_ENTITIES,

                            "aliases": aliases,
                            "version": 1,
                            "is_active": True,
                        }

                        records_to_upsert.append(record)

            # =========================
            # UPSERT (CRITICAL FIX)
            # =========================
            if not records_to_upsert:
                logger.warning("[EMPTY] No records to upsert")
                return None

            logger.info(f"[UPSERT] Upserting {len(records_to_upsert)} records")

            response = (
                self.client
                .table("terraform_registry")
                .upsert(
                    records_to_upsert,
                    on_conflict="terraform_key"
                )
                .execute()
            )

            logger.info("[SUCCESS] terraform_registry populated successfully")
            return response

        except Exception:
            logger.exception("[ERROR] Failed to populate terraform_registry")
            raise

    # ------------------------------------------------------------------ #
    # Shared helpers for child-table populators
    # ------------------------------------------------------------------ #
    def _registry_key_map(self):
        """Return {terraform_key: id} for all terraform_registry rows."""
        resp = (
            self.client
            .from_("terraform_registry")
            .select("id, terraform_key")
            .execute()
        )
        return {row["terraform_key"]: row["id"] for row in (resp.data or [])}

    def _resolve_registry_id(self, key, key_to_id):
        """
        Resolve a (possibly aliased / non-canonical) terraform_key to a
        terraform_registry.id. Tries the key directly, then TERRAFORM_KEY_ALIASES.
        Returns None if unresolved (caller logs + skips).
        """
        if key in key_to_id:
            return key_to_id[key]
        canonical = TERRAFORM_KEY_ALIASES.get(key)
        if canonical and canonical in key_to_id:
            return key_to_id[canonical]
        return None

    def populate_entity_field_rule(self):
        """
        Populate entity_field_rule from the four per-field mappings, each tagged
        with a rule_type:
          NON_EDITABLE_FIELDS    -> 'non_editable'    (keyed by display name)
          EXCLUDED_OUTPUT_FIELDS -> 'excluded_output' (list values; loose keys)
          ENTITY_TARGET_FIELD_MAP-> 'target_id'       (str|list values; tf_key)
          NONE_FIELD_LISTS       -> 'default'         (dict|set values; tf_key)
        Upserts on (terraform_registry_id, rule_type, field_name).
        """
        try:
            key_to_id = self._registry_key_map()

            # display-name -> terraform_key (NON_EDITABLE_FIELDS is keyed by display name)
            name_to_key = {
                entity_name: terraform_key
                for entity_list in RESOURCE_COLLECTION_MAP.values()
                for entity_map in entity_list
                for entity_name, terraform_key in entity_map.items()
            }

            records = []
            seen = set()

            def add(lookup_key, rule_type, field_name, default_value=None):
                if not field_name:
                    return
                registry_id = self._resolve_registry_id(lookup_key, key_to_id)
                if not registry_id:
                    logger.warning(
                        f"[SKIP] entity_field_rule: unresolved key {lookup_key!r} "
                        f"(rule_type={rule_type}, field={field_name})"
                    )
                    return
                dedup = (registry_id, rule_type, field_name)
                if dedup in seen:
                    return
                seen.add(dedup)
                records.append({
                    "terraform_registry_id": registry_id,
                    "rule_type": rule_type,
                    "field_name": field_name,
                    "default_value": default_value,
                    "is_active": True,
                    "version": 1,
                })

            # non_editable — keyed by display name
            for entity_name, fields in NON_EDITABLE_FIELDS.items():
                tf_key = name_to_key.get(entity_name, entity_name)
                for f in (fields or []):
                    add(tf_key, "non_editable", f)

            # excluded_output — list values; loose keys resolved via alias else skipped
            for key, fields in EXCLUDED_OUTPUT_FIELDS.items():
                values = fields if isinstance(fields, list) else [fields]
                for f in values:
                    add(key, "excluded_output", f)

            # target_id — str or list values, keyed by terraform_key
            for key, value in ENTITY_TARGET_FIELD_MAP.items():
                values = value if isinstance(value, list) else [value]
                for f in values:
                    add(key, "target_id", f)

            # default — dict {field: default} or set {field, ...}
            for key, spec in NONE_FIELD_LISTS.items():
                if isinstance(spec, dict):
                    for f, dv in spec.items():
                        add(key, "default", f, dv)
                else:  # set-valued entry -> default_value null
                    for f in spec:
                        add(key, "default", f, None)

            if not records:
                logger.warning("[EMPTY] No entity_field_rule records to upsert")
                return None

            logger.info(f"[UPSERT] Upserting {len(records)} entity_field_rule records")
            response = (
                self.client
                .table("entity_field_rule")
                .upsert(records, on_conflict="terraform_registry_id,rule_type,field_name")
                .execute()
            )
            logger.info("[SUCCESS] entity_field_rule populated successfully")
            return response

        except Exception:
            logger.exception("[ERROR] Failed to populate entity_field_rule")
            raise

    def populate_terraform_target(self):
        """
        Populate terraform_target from the full ENTITY_TARGET_PREFIX_MAP list
        (one row per target address, with sort_order preserving list order).
        Upserts on (terraform_registry_id, target_address).
        """
        try:
            key_to_id = self._registry_key_map()
            records = []

            for terraform_key, addresses in ENTITY_TARGET_PREFIX_MAP.items():
                registry_id = self._resolve_registry_id(terraform_key, key_to_id)
                if not registry_id:
                    logger.warning(
                        f"[SKIP] terraform_target: no registry row for {terraform_key}"
                    )
                    continue

                addr_list = addresses if isinstance(addresses, list) else [addresses]
                for idx, address in enumerate(addr_list):
                    if not address:
                        continue
                    records.append({
                        "terraform_registry_id": registry_id,
                        "target_address": address,
                        "sort_order": idx,
                    })

            if not records:
                logger.warning("[EMPTY] No terraform_target records to upsert")
                return None

            logger.info(f"[UPSERT] Upserting {len(records)} terraform_target records")
            response = (
                self.client
                .table("terraform_target")
                .upsert(records, on_conflict="terraform_registry_id,target_address")
                .execute()
            )
            logger.info("[SUCCESS] terraform_target populated successfully")
            return response

        except Exception:
            logger.exception("[ERROR] Failed to populate terraform_target")
            raise

    def populate_entity_dependency(self):
        """
        Populate entity_dependency from ENTITY_DEPENDENCY_MAPPING (cascade-delete
        graph). Parent keyed by terraform_key; one row per child entry. Upserts on
        (parent_registry_id, child_entity_name).
        """
        try:
            key_to_id = self._registry_key_map()
            records = []

            for parent_key, children in ENTITY_DEPENDENCY_MAPPING.items():
                parent_id = self._resolve_registry_id(parent_key, key_to_id)
                if not parent_id:
                    logger.warning(
                        f"[SKIP] entity_dependency: no registry row for parent {parent_key}"
                    )
                    continue

                for child in (children or []):
                    child_name = child.get("entity_name")
                    if not child_name:
                        continue
                    records.append({
                        "parent_registry_id": parent_id,
                        "child_entity_name": child_name,
                        "state_file": child.get("state_file", ""),
                        "resource_prefix": child.get("resource_prefix", ""),
                        "query_field": child.get("query_field", ""),
                        "id_field": child.get("id_field", ""),
                        "description": child.get("description", ""),
                    })

            if not records:
                logger.warning("[EMPTY] No entity_dependency records to upsert")
                return None

            logger.info(f"[UPSERT] Upserting {len(records)} entity_dependency records")
            response = (
                self.client
                .table("entity_dependency")
                .upsert(records, on_conflict="parent_registry_id,child_entity_name")
                .execute()
            )
            logger.info("[SUCCESS] entity_dependency populated successfully")
            return response

        except Exception:
            logger.exception("[ERROR] Failed to populate entity_dependency")
            raise

    def populate_parent_entity_mapping(self):
        """
        Populate parent_entity_mapping from the apps PARENT_ENTITY_MAPPINGS dict
        (child terraform_key -> {parent, id_field, no_fetch}). Key-based table
        (no FK), so it does not depend on registry rows. Upserts on
        child_terraform_key. PARENT_ENTITY_MAPPINGS is imported lazily to avoid
        importing a viewset module at service import time.
        """
        try:
            from entities.okta_entities.apps.views.apps_base_viewset import (
                PARENT_ENTITY_MAPPINGS,
            )

            records = []
            for child_key, cfg in PARENT_ENTITY_MAPPINGS.items():
                parent_key = (cfg or {}).get("parent")
                if not child_key or not parent_key:
                    continue
                records.append({
                    "child_terraform_key": child_key,
                    "parent_terraform_key": parent_key,
                    "id_field": cfg.get("id_field", ""),
                    "no_fetch": bool(cfg.get("no_fetch", False)),
                })

            if not records:
                logger.warning("[EMPTY] No parent_entity_mapping records to upsert")
                return None

            logger.info(f"[UPSERT] Upserting {len(records)} parent_entity_mapping records")
            response = (
                self.client
                .table("parent_entity_mapping")
                .upsert(records, on_conflict="child_terraform_key")
                .execute()
            )
            logger.info("[SUCCESS] parent_entity_mapping populated successfully")
            return response

        except Exception:
            logger.exception("[ERROR] Failed to populate parent_entity_mapping")
            raise

    def populate_okta_endpoint_attribute(self):
        """
        Fully populate okta_endpoint_attribute in ONE pass.

        Expands ENTITY_TYPE_MAPPING (terraform_key -> {"attributes": [...]})
        into one row per (okta_endpoint_id, attribute_name). okta_endpoint_id
        is the terraform_registry.id resolved via terraform_key.
        """

        try:
            registry_resp = (
                self.client
                .from_("terraform_registry")
                .select("id, terraform_key")
                .execute()
            )
            registry_id_by_key = {
                row["terraform_key"]: row["id"]
                for row in (registry_resp.data or [])
            }

            records_to_upsert = []

            for terraform_key, config in ENTITY_TYPE_MAPPING.items():
                logger.debug(f"[ENTITY] Processing terraform_key: {terraform_key}")

                attributes = (config or {}).get("attributes") or []
                if not attributes:
                    logger.warning(f"[SKIP] No attributes defined for {terraform_key}")
                    continue

                terraform_registry_id = registry_id_by_key.get(terraform_key)
                if not terraform_registry_id:
                    logger.warning(
                        f"[SKIP] No terraform_registry row for terraform_key={terraform_key}; "
                        f"run populate_terraform_registry first"
                    )
                    continue

                for attribute_name in attributes:
                    if not attribute_name:
                        continue
                    records_to_upsert.append({
                        "terraform_registry_id": terraform_registry_id,
                        "attribute_name": attribute_name,
                    })

            if not records_to_upsert:
                logger.warning("[EMPTY] No records to upsert")
                return None

            logger.info(f"[UPSERT] Upserting {len(records_to_upsert)} okta_endpoint_attribute records")

            response = (
                self.client
                .table("okta_endpoint_attribute")
                .upsert(
                    records_to_upsert,
                    on_conflict="terraform_registry_id,attribute_name",
                )
                .execute()
            )

            logger.info("[SUCCESS] okta_endpoint_attribute populated successfully")
            return response

        except Exception:
            logger.exception("[ERROR] Failed to populate okta_endpoint_attribute")
            raise

    @staticmethod
    def _resolve_child_resource_address(parent_config, child_id_field, child_resource):
        """
        Resolve a child's Terraform resource address from a NESTED_ENTITY_CONFIG
        entry, which has two shapes:
          - flat:      {"child_resource": "..."}                      (single child)
          - children:  {"children": [{"child_id_field": .., "child_resource": ..}]}

        For the children[] shape, match primarily on the child resource TYPE — the
        third dotted segment of the address (module.<mod>.<resource_type>.<name>)
        must equal child_resource (the child terraform_key). This is exact and
        avoids the child_id_field disagreement between the bdt and OkTf source
        dicts (e.g. trusted_servers: bdt 'auth_server_id' vs OkTf 'trusted_id').
        Falls back to a child_id_field match, then None (never the first child).
        """
        if not parent_config:
            return None
        children = parent_config.get("children")
        if not children:
            return parent_config.get("child_resource")

        # 1) exact resource-type match
        if child_resource:
            for child in children:
                address = child.get("child_resource") or ""
                parts = address.split(".")
                if len(parts) >= 3 and parts[2] == child_resource:
                    return address
        # 2) fall back to child_id_field match
        for child in children:
            if child.get("child_id_field") == child_id_field:
                return child.get("child_resource")
        # 3) no reliable match
        return None

    def populate_nested_entity_mapping(self):
        """
        Populate nested_entity_mapping in ONE pass by joining several mappings,
        one row per (terraform_registry_id, child_field_name):
          NESTED_FIELD_COLLECTIONS (parent display name -> {child_field: child_resource})
          NESTED_FIELD_ID_MAPPING  (child_field -> {parent_id_field, child_id_field})
          OkTf NESTED_ENTITY_KEYS  (parent wrapper_key -> {child_field: child_unique_key})
          OkTf NESTED_ENTITY_CONFIG(parent tf_key -> parent/child resource addresses)
        """

        try:
            registry_id_by_key = self._registry_key_map()

            entity_to_terraform_key = {
                entity_name: terraform_key
                for entity_list in RESOURCE_COLLECTION_MAP.values()
                for entity_map in entity_list
                for entity_name, terraform_key in entity_map.items()
            }

            records_to_upsert = []

            for parent_entity_name, child_fields in NESTED_FIELD_COLLECTIONS.items():
                logger.debug(f"[ENTITY] Processing parent: {parent_entity_name}")

                # NESTED_FIELD_COLLECTIONS is keyed by DISPLAY label ("Auth Server")
                parent_terraform_key = entity_to_terraform_key.get(parent_entity_name)
                if not parent_terraform_key:
                    logger.warning(
                        f"[SKIP] No terraform_key in RESOURCE_COLLECTION_MAP for "
                        f"parent entity_name={parent_entity_name}"
                    )
                    continue

                terraform_registry_id = registry_id_by_key.get(parent_terraform_key)
                if not terraform_registry_id:
                    logger.warning(
                        f"[SKIP] No terraform_registry row for terraform_key={parent_terraform_key}; "
                        f"run populate_terraform_registry first"
                    )
                    continue

                # OkTf lookups (keyed by wrapper key / terraform key)
                parent_wrapper_key = ENTITY_FIELD_MAPPING.get(parent_terraform_key, "")
                nested_unique_keys = NESTED_ENTITY_KEYS.get(parent_wrapper_key, {})
                parent_config = NESTED_ENTITY_CONFIG.get(parent_terraform_key, {})
                parent_resource_address = parent_config.get("parent_resource")

                for child_field_name, child_resource in (child_fields or {}).items():
                    id_mapping = NESTED_FIELD_ID_MAPPING.get(child_field_name) or {}
                    child_id_field = id_mapping.get("child_id_field")

                    if not child_field_name or not child_id_field:
                        logger.warning(
                            f"[SKIP] Missing child_id_field for {parent_entity_name}.{child_field_name}"
                        )
                        continue

                    records_to_upsert.append({
                        "terraform_registry_id": terraform_registry_id,
                        "child_field_name": child_field_name,
                        "child_resource": child_resource or None,
                        "parent_id_field": id_mapping.get("parent_id_field"),
                        "child_id_field": child_id_field,
                        "child_unique_key": nested_unique_keys.get(child_field_name),
                        "parent_resource_address": parent_resource_address,
                        "child_resource_address": self._resolve_child_resource_address(
                            parent_config, child_id_field, child_resource
                        ),
                    })

            if not records_to_upsert:
                logger.warning("[EMPTY] No records to upsert")
                return None

            logger.info(f"[UPSERT] Upserting {len(records_to_upsert)} nested_entity_mapping records")

            response = (
                self.client
                .table("nested_entity_mapping")
                .upsert(
                    records_to_upsert,
                    on_conflict="terraform_registry_id,child_field_name",
                )
                .execute()
            )

            logger.info("[SUCCESS] nested_entity_mapping populated successfully")
            return response

        except Exception:
            logger.exception("[ERROR] Failed to populate nested_entity_mapping")
            raise



