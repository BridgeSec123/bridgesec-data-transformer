"""
Entity configuration utilities — per-tenant backup entity and collection selection.

get_enabled_entities_for_tenant(tenant_id)
    Returns the set of entity names that should be backed up for a tenant.
    Fallback chain:
        1. entity_catalog (is_active=True) minus tenant's disabled list
        2. If catalog is empty → fall back to ENTITY_VIEWSETS keys
        3. If Supabase unreachable → fall back to ENTITY_VIEWSETS keys

get_entity_catalog_with_status(tenant_id)
    Returns full catalog list with per-tenant enabled/disabled status for both
    entities and individual collections within each entity.
    Used by the API to render the entity config UI.

bulk_update_entity_config(tenant_id, updates, updated_by)
    Batch upsert enabled/disabled overrides for a tenant.
    Accepts mixed entity-level and collection-level entries in one call.

toggle_collection_config(tenant_id, entity_name, collection_name, enabled, updated_by)
    Upsert a single collection-level override.

get_disabled_collections_for_tenant(tenant_id)
    Returns {entity_name: set(disabled_collection_names)} for the backup worker.
"""
import json
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def _get_supabase():
    from core.utils.supabase_client import get_supabase_client
    return get_supabase_client()


def _fallback_entity_names() -> set:
    """Return all keys from the hardcoded ENTITY_VIEWSETS as the safe fallback."""
    from entities.registry import ENTITY_VIEWSETS
    return set(ENTITY_VIEWSETS.keys())


def _get_collection_config_map(sb, tenant_id) -> dict:
    """
    Internal helper. Query tenant_collection_config and return
    {entity_name: {collection_name: enabled}} for this tenant.
    """
    query = sb.table("tenant_collection_config").select("entity_name, collection_name, enabled")
    if tenant_id:
        query = query.eq("tenant_id", str(tenant_id))
    else:
        query = query.is_("tenant_id", "null")

    rows = query.execute().data or []
    result: dict = {}
    for row in rows:
        result.setdefault(row["entity_name"], {})[row["collection_name"]] = row["enabled"]
    return result


def get_enabled_entities_for_tenant(tenant_id) -> set:
    """
    Return the set of entity names enabled for backup for this tenant.

    Logic:
    - Base set = entity_catalog rows where is_active=True
    - Subtract = tenant_entity_config rows where enabled=False for this tenant
    - No config row for an entity → enabled by default (safe default)
    - Empty catalog or Supabase unreachable → falls back to ENTITY_VIEWSETS keys
    """
    try:
        sb = _get_supabase()

        active_resp = (
            sb.table("entity_catalog")
            .select("name")
            .eq("is_active", True)
            .execute()
        )
        active_entities = {row["name"] for row in (active_resp.data or [])}

        # Guard: empty catalog means seed hasn't run — use hardcoded fallback
        if not active_entities:
            logger.warning(
                "entity_catalog is empty — seed_entity_catalog has not been run. "
                "Falling back to ENTITY_VIEWSETS for this backup run."
            )
            return _fallback_entity_names()

        # Fetch tenant's explicit disabled overrides
        query = sb.table("tenant_entity_config").select("entity_name, enabled")
        if tenant_id:
            query = query.eq("tenant_id", str(tenant_id))
        else:
            query = query.is_("tenant_id", "null")

        config_resp = query.execute()
        disabled = {
            row["entity_name"]
            for row in (config_resp.data or [])
            if not row["enabled"]
        }

        return active_entities - disabled

    except Exception as exc:
        logger.warning(
            "Supabase unreachable while resolving entity config "
            f"(tenant_id={tenant_id}): {exc}. "
            "Falling back to full ENTITY_VIEWSETS for this backup run."
        )
        return _fallback_entity_names()


def get_disabled_collections_for_tenant(tenant_id) -> dict:
    """
    Return {entity_name: set(disabled_collection_names)} for this tenant.

    Used by the backup worker to skip individual collections that the tenant
    has explicitly disabled. Returns {} on any error (safe default — back up
    everything rather than accidentally skipping).
    """
    try:
        sb = _get_supabase()
        query = sb.table("tenant_collection_config").select("entity_name, collection_name, enabled")
        if tenant_id:
            query = query.eq("tenant_id", str(tenant_id))
        else:
            query = query.is_("tenant_id", "null")

        rows = query.execute().data or []
        result: dict = {}
        for row in rows:
            if not row["enabled"]:
                result.setdefault(row["entity_name"], set()).add(row["collection_name"])
        return result

    except Exception as exc:
        logger.warning(
            "Supabase unreachable while resolving collection config "
            f"(tenant_id={tenant_id}): {exc}. "
            "Skipping collection-level filtering for this backup run."
        )
        return {}


def get_excluded_app_ids_for_tenant(tenant) -> set:
    """
    Return the set of Okta app IDs that should be excluded from the bulk fetch
    for this tenant (service app and OIDC app).
    Returns an empty set when the tenant is None or both fields are unset.
    """
    if not tenant:
        return set()
    ids = set()
    if getattr(tenant, "service_app_id", None):
        ids.add(tenant.service_app_id)
    if getattr(tenant, "oidc_app_id", None):
        ids.add(tenant.oidc_app_id)
    return ids


def get_entity_catalog_with_status(tenant_id) -> list:
    """
    Return all catalog entries merged with this tenant's enabled/disabled config
    at both the entity level and collection level.

    Each item:
    {
        name, display_name, category, description,
        collections: [
            {display_name, collection_name, id_field, is_active, enabled},
            ...
        ],
        is_active,
        enabled,        # False only if tenant explicitly disabled this entity
        updated_at,
        updated_by,
    }
    Sorted by category then display_name.
    """
    try:
        sb = _get_supabase()

        catalog_resp = sb.table("entity_catalog").select("*").execute()
        catalog = {row["name"]: row for row in (catalog_resp.data or [])}

        # Entity-level overrides
        query = sb.table("tenant_entity_config").select("*")
        if tenant_id:
            query = query.eq("tenant_id", str(tenant_id))
        else:
            query = query.is_("tenant_id", "null")

        config_resp = query.execute()
        config_map = {row["entity_name"]: row for row in (config_resp.data or [])}

        # Collection-level overrides (table may not exist if migration 006 hasn't run yet)
        try:
            collection_config_map = _get_collection_config_map(sb, tenant_id)
        except Exception as col_exc:
            logger.warning(f"Could not load collection config (migration pending?): {col_exc}")
            collection_config_map = {}

        result = []
        for name, cat_row in catalog.items():
            cfg = config_map.get(name, {})
            entity_enabled = cfg.get("enabled", True)

            collections = cat_row.get("collections") or []
            if isinstance(collections, str):
                try:
                    collections = json.loads(collections)
                except Exception:
                    collections = []

            col_overrides = collection_config_map.get(name, {})
            collections_with_status = [
                {
                    **col,
                    "is_active": col.get("is_active", True),
                    "enabled": col_overrides.get(col["collection_name"], entity_enabled),
                }
                for col in collections
            ]

            result.append({
                "name":         name,
                "display_name": cat_row["display_name"],
                "category":     cat_row["category"],
                "description":  cat_row.get("description", ""),
                "collections":  collections_with_status,
                "is_active":    cat_row.get("is_active", False),
                "enabled":      entity_enabled,
                "updated_at":   cfg.get("updated_at"),
                "updated_by":   cfg.get("updated_by"),
            })

        result.sort(key=lambda x: (x["category"], x["display_name"]))
        return result

    except Exception as exc:
        logger.warning(f"get_entity_catalog_with_status failed (tenant_id={tenant_id}): {exc}")
        return []


def toggle_collection_config(
    tenant_id,
    entity_name: str,
    collection_name: str,
    enabled: bool,
    updated_by: str,
) -> dict:
    """
    Upsert a single collection-level enabled/disabled override.

    Returns {"updated": 1, "errors": []} on success.
    """
    sb = _get_supabase()
    try:
        from datetime import datetime, timezone
        row = {
            "entity_name":     entity_name,
            "collection_name": collection_name,
            "enabled":         bool(enabled),
            "updated_at":      datetime.now(timezone.utc).isoformat(),
            "updated_by":      updated_by or "",
            "tenant_id":       str(tenant_id) if tenant_id else None,
        }

        # Check for existing row
        existing_q = (
            sb.table("tenant_collection_config")
            .select("id")
            .eq("entity_name", entity_name)
            .eq("collection_name", collection_name)
        )
        if tenant_id:
            existing_q = existing_q.eq("tenant_id", str(tenant_id))
        else:
            existing_q = existing_q.is_("tenant_id", "null")
        existing_rows = existing_q.execute().data or []

        if existing_rows:
            sb.table("tenant_collection_config").update(row).eq("id", existing_rows[0]["id"]).execute()
        else:
            sb.table("tenant_collection_config").insert(row).execute()

        return {"updated": 1, "errors": []}

    except Exception as exc:
        logger.warning(f"toggle_collection_config error for {entity_name}/{collection_name}: {exc}")
        return {"updated": 0, "errors": [f"{entity_name}/{collection_name}: {exc}"]}


def bulk_update_entity_config(tenant_id, updates: list, updated_by: str) -> dict:
    """
    Batch upsert tenant_entity_config and/or tenant_collection_config rows.

    updates: [
        {"name": "users", "enabled": True},                          # entity-level
        {"name": "apps", "collection": "app_oauth", "enabled": False},  # collection-level
        ...
    ]
    Entity-level entries are processed before collection-level entries.
    Returns {"updated": <count>, "errors": [...]}
    """
    entity_updates = [u for u in updates if "collection" not in u]
    collection_updates = [u for u in updates if "collection" in u]

    sb = _get_supabase()
    updated_count = 0
    errors = []

    # --- Entity-level (existing logic, unchanged) ---
    for item in entity_updates:
        entity_name = item.get("name")
        enabled = item.get("enabled")
        if entity_name is None or enabled is None:
            errors.append(f"Invalid entry: {item}")
            continue

        try:
            from datetime import datetime, timezone
            row = {
                "entity_name": entity_name,
                "enabled":     bool(enabled),
                "updated_at":  datetime.now(timezone.utc).isoformat(),
                "updated_by":  updated_by or "",
                "tenant_id":   str(tenant_id) if tenant_id else None,
            }

            existing_q = sb.table("tenant_entity_config").select("id").eq("entity_name", entity_name)
            if tenant_id:
                existing_q = existing_q.eq("tenant_id", str(tenant_id))
            else:
                existing_q = existing_q.is_("tenant_id", "null")
            existing_rows = existing_q.execute().data or []

            if existing_rows:
                sb.table("tenant_entity_config").update(row).eq("id", existing_rows[0]["id"]).execute()
            else:
                sb.table("tenant_entity_config").insert(row).execute()

            updated_count += 1

        except Exception as exc:
            errors.append(f"{entity_name}: {exc}")
            logger.warning(f"bulk_update_entity_config error for {entity_name}: {exc}")

    # --- Collection-level ---
    for item in collection_updates:
        entity_name = item.get("name")
        collection_name = item.get("collection")
        enabled = item.get("enabled")
        if not entity_name or not collection_name or enabled is None:
            errors.append(f"Invalid collection entry: {item}")
            continue

        result = toggle_collection_config(tenant_id, entity_name, collection_name, bool(enabled), updated_by)
        if result["errors"]:
            errors.extend(result["errors"])
        else:
            updated_count += 1

    return {"updated": updated_count, "errors": errors}
