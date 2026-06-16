"""
mapping_provider.py — Django-agnostic Supabase-backed mapping registry.

All in-code mapping dicts (RESOURCE_COLLECTION_MAP, ENTITY_ID_MAPPING, …) are
rebuilt from the Supabase ``terraform_registry`` + child tables. Results are
cached with a configurable TTL (default 300 s) and every accessor falls back to
the caller-supplied in-code dict when Supabase is unavailable or the table is
empty.

Quick-start (call once at app startup — e.g. in Django's AppConfig.ready()):

    from bridgesec_logging.mapping_provider import configure
    configure(
        client_getter=lambda: get_supabase_client(),
        fallbacks={
            "RESOURCE_COLLECTION_MAP": RESOURCE_COLLECTION_MAP,
            "ENTITY_ID_MAPPING": ENTITY_ID_MAPPING,
            # … all remaining in-code registries …
        },
        ttl_sec=300,
    )

After a re-seed call ``refresh()`` to invalidate the cache immediately.
"""

import importlib
import logging
import threading
import time

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal state
# ---------------------------------------------------------------------------

_lock = threading.Lock()


class _State:
    __slots__ = ("client_getter", "fallbacks", "ttl_sec", "_data", "_fetched_at")

    def __init__(self):
        self.client_getter = None   # callable() → supabase client
        self.fallbacks: dict = {}   # {name: in-code registry}
        self.ttl_sec: float = 300.0
        self._data = None           # dict of all reconstructed registries
        self._fetched_at: float = 0.0


_state = _State()


# ---------------------------------------------------------------------------
# Public configuration API
# ---------------------------------------------------------------------------

def configure(client_getter, fallbacks=None, ttl_sec=300):
    """
    Configure the provider.  Call once per process before using any accessor.

    :param client_getter: Zero-argument callable that returns a supabase client.
    :param fallbacks: Dict ``{registry_name: in_code_dict}`` used when Supabase
        is unavailable. The keys must match the REGISTRY_NAME constants used in
        this module (RESOURCE_COLLECTION_MAP, ENTITY_ID_MAPPING, …).
    :param ttl_sec: Seconds before the cached snapshot is considered stale.
    """
    with _lock:
        _state.client_getter = client_getter
        _state.fallbacks = fallbacks or {}
        _state.ttl_sec = float(ttl_sec)
        _state._data = None
        _state._fetched_at = 0.0


def refresh():
    """Force-invalidate the cache.  The next accessor call will refetch."""
    with _lock:
        _state._data = None
        _state._fetched_at = 0.0


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _is_stale() -> bool:
    if _state._data is None:
        return True
    return (time.monotonic() - _state._fetched_at) > _state.ttl_sec


def _get_client():
    if _state.client_getter is not None:
        return _state.client_getter()
    # Environment-variable fallback (useful without Django / before configure())
    import os
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if url and key:
        try:
            from supabase import create_client
            return create_client(url, key)
        except Exception:
            pass
    return None


def _ensure_fresh():
    """Check TTL and rebuild cache if stale. Thread-safe (double-checked lock)."""
    if not _is_stale():
        return
    with _lock:
        if not _is_stale():          # another thread may have rebuilt while we waited
            return
        try:
            _rebuild()
        except Exception as exc:
            logger.warning(
                "[mapping_provider] Supabase fetch failed — using in-code fallbacks. "
                "Error: %s", exc
            )


def _rebuild():
    """Fetch all tables, reconstruct all registries, store in _state._data."""
    client = _get_client()
    if client is None:
        logger.warning("[mapping_provider] No Supabase client available — keeping fallbacks")
        return

    # ---- Fetch terraform_registry ----------------------------------------
    registry_rows = client.table("terraform_registry").select("*").execute().data or []
    if not registry_rows:
        logger.warning("[mapping_provider] terraform_registry is empty — using fallbacks")
        return

    # Build id → row lookup for child-table joins
    id_to_row = {row["id"]: row for row in registry_rows}

    # ---- Fetch child tables ----------------------------------------------
    try:
        field_rules = (
            client.table("entity_field_rule").select("*").execute().data or []
        )
    except Exception as exc:
        logger.warning("[mapping_provider] entity_field_rule fetch failed: %s", exc)
        field_rules = []

    try:
        targets = (
            client.table("terraform_target")
            .select("*")
            .order("sort_order")
            .execute()
            .data or []
        )
    except Exception as exc:
        logger.warning("[mapping_provider] terraform_target fetch failed: %s", exc)
        targets = []

    try:
        attributes = (
            client.table("okta_endpoint_attribute").select("*").execute().data or []
        )
    except Exception as exc:
        logger.warning("[mapping_provider] okta_endpoint_attribute fetch failed: %s", exc)
        attributes = []

    try:
        nested = (
            client.table("nested_entity_mapping").select("*").execute().data or []
        )
    except Exception as exc:
        logger.warning("[mapping_provider] nested_entity_mapping fetch failed: %s", exc)
        nested = []

    # ---- Build all derived dicts -----------------------------------------
    data = _build_all(registry_rows, id_to_row, field_rules, targets, attributes, nested)
    _state._data = data
    _state._fetched_at = time.monotonic()
    logger.info(
        "[mapping_provider] Cache refreshed — %d terraform_registry rows loaded",
        len(registry_rows),
    )


def _build_all(registry_rows, id_to_row, field_rules, targets, attributes, nested) -> dict:  # noqa: C901
    """Reconstruct every derived registry from raw table rows."""

    # ------------------------------------------------------------------
    # Pre-index child table rows by terraform_registry_id
    # ------------------------------------------------------------------

    # entity_field_rule: {(registry_id, rule_type): [row, ...]}
    rules_by_id_type: dict = {}
    for r in field_rules:
        k = (r["terraform_registry_id"], r["rule_type"])
        rules_by_id_type.setdefault(k, []).append(r)

    # terraform_target: {registry_id: [address, ...]} (already sorted by sort_order)
    targets_by_id: dict = {}
    for t in sorted(targets, key=lambda x: x.get("sort_order") or 0):
        targets_by_id.setdefault(t["terraform_registry_id"], []).append(
            t["target_address"]
        )

    # okta_endpoint_attribute: {registry_id: [attribute_name, ...]}
    attrs_by_id: dict = {}
    for a in attributes:
        attrs_by_id.setdefault(a["terraform_registry_id"], []).append(
            a["attribute_name"]
        )

    # nested_entity_mapping: {registry_id: [row, ...]}
    nested_by_id: dict = {}
    for n in nested:
        nested_by_id.setdefault(n["terraform_registry_id"], []).append(n)

    # Sort registry rows by id for stable (insertion-order) output
    sorted_rows = sorted(registry_rows, key=lambda r: r.get("id") or "")

    data: dict = {}

    # ------------------------------------------------------------------
    # RESOURCE_COLLECTION_MAP  →  {category: [{display_name: tf_key}, ...]}
    # ------------------------------------------------------------------
    rcm: dict = {}
    for row in sorted_rows:
        cat = row.get("category", "") or ""
        if not cat:
            continue
        rcm.setdefault(cat, []).append({row["display_name"]: row["terraform_key"]})
    data["RESOURCE_COLLECTION_MAP"] = rcm

    # ------------------------------------------------------------------
    # ENTITY_ID_MAPPING  →  {display_name: id_key}
    # ------------------------------------------------------------------
    eim: dict = {}
    for row in sorted_rows:
        id_key = row.get("id_key") or ""
        if id_key:
            eim[row["display_name"]] = id_key
    data["ENTITY_ID_MAPPING"] = eim

    # ------------------------------------------------------------------
    # NON_EDITABLE_FIELDS  →  {display_name: [field, ...]}
    # ------------------------------------------------------------------
    nef: dict = {}
    for row in sorted_rows:
        rid = row.get("id")
        rules = rules_by_id_type.get((rid, "non_editable"), [])
        if rules:
            nef[row["display_name"]] = [r["field_name"] for r in rules]
    data["NON_EDITABLE_FIELDS"] = nef

    # ------------------------------------------------------------------
    # EXCLUDED_OUTPUT_FIELDS  →  {tf_key: [field, ...] or str}
    # ------------------------------------------------------------------
    eof_data: dict = {}
    for row in sorted_rows:
        rid = row.get("id")
        rules = rules_by_id_type.get((rid, "excluded_output"), [])
        if rules:
            fields = [r["field_name"] for r in rules]
            eof_data[row["terraform_key"]] = fields if len(fields) > 1 else fields[0]
    data["EXCLUDED_OUTPUT_FIELDS"] = eof_data

    # ------------------------------------------------------------------
    # ENTITY_TARGET_FIELD_MAP  →  {tf_key: str | list}
    # Preserve string vs list distinction: 1 field → str, >1 → list
    # ------------------------------------------------------------------
    etfm: dict = {}
    for row in sorted_rows:
        rid = row.get("id")
        rules = rules_by_id_type.get((rid, "target_id"), [])
        if rules:
            fields = [r["field_name"] for r in rules]
            etfm[row["terraform_key"]] = fields if len(fields) > 1 else fields[0]
    data["ENTITY_TARGET_FIELD_MAP"] = etfm

    # ------------------------------------------------------------------
    # NONE_FIELD_LISTS  →  {tf_key: {field: default_value}}
    # Set-typed entries in the original code become dicts with None values —
    # iteration over them (for field in ...) is identical behaviour.
    # ------------------------------------------------------------------
    nfl: dict = {}
    for row in sorted_rows:
        rid = row.get("id")
        rules = rules_by_id_type.get((rid, "default"), [])
        if rules:
            nfl[row["terraform_key"]] = {r["field_name"]: r.get("default_value") for r in rules}
    data["NONE_FIELD_LISTS"] = nfl

    # ------------------------------------------------------------------
    # ENTITY_TARGET_PREFIX_MAP  →  {tf_key: [address, ...]}
    # ------------------------------------------------------------------
    etpm: dict = {}
    for row in sorted_rows:
        rid = row.get("id")
        addrs = targets_by_id.get(rid, [])
        if addrs:
            etpm[row["terraform_key"]] = addrs
    data["ENTITY_TARGET_PREFIX_MAP"] = etpm

    # ------------------------------------------------------------------
    # ENTITY_TYPE_MAPPING  →  {tf_key: {"okta_endpoint": ..., "attributes": [...]}}
    # ------------------------------------------------------------------
    etm: dict = {}
    for row in sorted_rows:
        rid = row.get("id")
        endpoint = row.get("okta_endpoint") or ""
        if not endpoint:
            continue
        etm[row["terraform_key"]] = {
            "okta_endpoint": endpoint,
            "attributes": attrs_by_id.get(rid, []),
        }
    data["ENTITY_TYPE_MAPPING"] = etm

    # ------------------------------------------------------------------
    # ID_KEYS  →  {tf_key: id_key}
    # ------------------------------------------------------------------
    id_keys: dict = {}
    for row in sorted_rows:
        ik = row.get("id_key") or ""
        if ik:
            id_keys[row["terraform_key"]] = ik
    data["ID_KEYS"] = id_keys

    # ------------------------------------------------------------------
    # RULES_FIELDS  →  {tf_key: rules_field}
    # ------------------------------------------------------------------
    rfields: dict = {}
    for row in sorted_rows:
        rf = row.get("rules_field") or ""
        if rf:
            rfields[row["terraform_key"]] = rf
    data["RULES_FIELDS"] = rfields

    # ------------------------------------------------------------------
    # ENTITY_UNIQUE_FIELDS (tf_key-keyed)  →  {tf_key: unique_key}
    # ------------------------------------------------------------------
    euf: dict = {}
    for row in sorted_rows:
        uk = row.get("unique_key") or ""
        if uk:
            euf[row["terraform_key"]] = uk
    data["ENTITY_UNIQUE_FIELDS"] = euf

    # ------------------------------------------------------------------
    # SINGLETON_RESOURCE_IDENTIFIERS  →  {tf_key: identifier}
    # ------------------------------------------------------------------
    sri: dict = {}
    for row in sorted_rows:
        if row.get("singleton_entity"):
            sri[row["terraform_key"]] = row.get("singleton_identifier") or ""
    data["SINGLETON_RESOURCE_IDENTIFIERS"] = sri

    # ------------------------------------------------------------------
    # ENTITY_IMPORT_MAPPING  →  {tf_key: {import_address, okta_id_field, …}}
    # ------------------------------------------------------------------
    imp_map: dict = {}
    for row in sorted_rows:
        if row.get("import_address"):
            imp_map[row["terraform_key"]] = {
                "import_address":       row.get("import_address", ""),
                "okta_id_field":        row.get("okta_id_field", ""),
                "terraform_key_field":  row.get("terraform_key_field", ""),
                "import_id_format":     row.get("import_id_format", ""),
                "terraform_key_format": row.get("terraform_key_format", ""),
            }
    data["ENTITY_IMPORT_MAPPING"] = imp_map

    # ------------------------------------------------------------------
    # NESTED_FIELD_COLLECTIONS  →  {display_name: {child_field: child_resource}}
    # ------------------------------------------------------------------
    nfc: dict = {}
    for row in sorted_rows:
        rid = row.get("id")
        nrows = nested_by_id.get(rid, [])
        if nrows:
            child_map = {
                n["child_field_name"]: n.get("child_resource")
                for n in nrows
                if n.get("child_field_name")
            }
            if child_map:
                nfc[row["display_name"]] = child_map
    data["NESTED_FIELD_COLLECTIONS"] = nfc

    # ------------------------------------------------------------------
    # NESTED_FIELD_ID_MAPPING  →  {child_field: {parent_id_field, child_id_field}}
    # ------------------------------------------------------------------
    nfidm: dict = {}
    for row in sorted_rows:
        rid = row.get("id")
        for n in nested_by_id.get(rid, []):
            cf = n.get("child_field_name")
            if cf:
                nfidm[cf] = {
                    "parent_id_field": n.get("parent_id_field"),
                    "child_id_field":  n.get("child_id_field"),
                }
    data["NESTED_FIELD_ID_MAPPING"] = nfidm

    # ------------------------------------------------------------------
    # ENTITIES_WITH_BUILDERS  →  [display_name, ...]
    # ------------------------------------------------------------------
    data["ENTITIES_WITH_BUILDERS"] = [
        row["display_name"] for row in sorted_rows if row.get("has_builders")
    ]

    # ------------------------------------------------------------------
    # WRAPPER_MAP (ENTITY_FIELD_MAPPING)  →  {tf_key: wrapper_key}
    # ------------------------------------------------------------------
    wrapper_map: dict = {}
    for row in sorted_rows:
        wk = row.get("wrapper_key") or ""
        if wk:
            wrapper_map[row["terraform_key"]] = wk
    data["WRAPPER_MAP"] = wrapper_map

    # ------------------------------------------------------------------
    # STATE_FILE_MAP (COLLECTION_STATE_MAP)  →  {tf_key: state_file_path}
    # ------------------------------------------------------------------
    sfm: dict = {}
    for row in sorted_rows:
        sfp = row.get("state_file_path") or ""
        if sfp:
            sfm[row["terraform_key"]] = sfp
    data["STATE_FILE_MAP"] = sfm

    # ------------------------------------------------------------------
    # GROUPED_ENTITIES  →  set of tf_keys that use composite keys
    # ------------------------------------------------------------------
    data["GROUPED_ENTITIES"] = {
        row["terraform_key"] for row in sorted_rows if row.get("uses_composite_key")
    }

    # ------------------------------------------------------------------
    # NESTED_ENTITY_CONFIG (OkTf)  →  {tf_key: {parent_resource, child_resource|children}}
    # ------------------------------------------------------------------
    nec: dict = {}
    for row in sorted_rows:
        rid = row.get("id")
        nrows = nested_by_id.get(rid, [])
        if not nrows:
            continue
        parent_resource = nrows[0].get("parent_resource_address")
        children = [
            {
                "child_id_field": n.get("child_id_field"),
                "child_resource": n.get("child_resource_address"),
            }
            for n in nrows
            if n.get("child_id_field")
        ]
        if not children:
            continue
        entry: dict = {}
        if parent_resource:
            entry["parent_resource"] = parent_resource
        if len(children) == 1:
            entry["child_resource"] = children[0].get("child_resource")
            entry["child_id_field"] = children[0].get("child_id_field")
        else:
            entry["children"] = children
        nec[row["terraform_key"]] = entry
    data["NESTED_ENTITY_CONFIG"] = nec

    # ------------------------------------------------------------------
    # NESTED_ENTITY_KEYS (OkTf, wrapper-keyed)
    #   →  {wrapper_key: {child_field_name: child_unique_key}}
    # This is the NESTED structure used for child-array deduplication.
    # NOTE: The flat ENTITY_UNIQUE_KEYS map ({wrapper_key: "field_str"}) is
    # NOT reconstructible from this table — its accessor always uses the
    # caller-supplied in-code fallback.
    # ------------------------------------------------------------------
    nek: dict = {}
    for row in sorted_rows:
        rid = row.get("id")
        wk = row.get("wrapper_key") or ""
        if not wk:
            continue
        nested_map = {
            n["child_field_name"]: n["child_unique_key"]
            for n in nested_by_id.get(rid, [])
            if n.get("child_field_name") and n.get("child_unique_key")
        }
        if nested_map:
            nek[wk] = nested_map
    data["NESTED_ENTITY_KEYS"] = nek
    # ENTITY_UNIQUE_KEYS (flat {wrapper_key: "field_str"}) intentionally
    # omitted — accessor always defers to the in-code fallback.

    # ------------------------------------------------------------------
    # BASE_API_PATH  →  {display_name: base_api_path}
    # ------------------------------------------------------------------
    bap: dict = {}
    for row in sorted_rows:
        p = row.get("base_api_path") or ""
        if p:
            bap[row["display_name"]] = p
    data["BASE_API_PATH"] = bap

    # ------------------------------------------------------------------
    # _MODEL_MAP / _SERIALIZER_MAP  (lazy importlib resolution)
    # Stored as {display_name: (module_path, class_name)} to defer the actual
    # import to get_model_registry() / get_serializer_registry().
    # ------------------------------------------------------------------
    model_map: dict = {}
    for row in sorted_rows:
        mp = row.get("model_module_path") or ""
        mc = row.get("model_class") or ""
        if mp and mc:
            model_map[row["display_name"]] = (mp, mc)
    data["_MODEL_MAP"] = model_map

    serializer_map: dict = {}
    for row in sorted_rows:
        mp = row.get("serializer_module_path") or ""
        mc = row.get("serializer_class") or ""
        if mp and mc:
            serializer_map[row["display_name"]] = (mp, mc)
    data["_SERIALIZER_MAP"] = serializer_map

    return data


# ---------------------------------------------------------------------------
# Private fallback helpers
# ---------------------------------------------------------------------------

def _fb(name, default=None):
    """Return the caller-supplied in-code fallback for a registry name."""
    return _state.fallbacks.get(name, default if default is not None else {})


def _merge(supabase_data, fallback):
    """
    Merge Supabase data with in-code fallback so that:
      - Keys present in fallback but absent from Supabase are filled in (no gaps)
      - Keys present in both: **fallback wins** (protects against stale/wrong Supabase values)
      - Keys present only in Supabase (new data added post-seed): preserved

    Pattern:  {**supabase_data, **fallback}
    (Python merge semantics: right dict overrides left on conflict)

    Returns supabase_data when fallback is empty/None, and fallback when
    supabase_data is empty/None.
    """
    if not supabase_data:
        return fallback if fallback is not None else {}
    if not fallback:
        return supabase_data
    return {**supabase_data, **fallback}


# ---------------------------------------------------------------------------
# Public accessor functions
# ---------------------------------------------------------------------------
# All accessors follow the same pattern:
#   1. ensure cache is fresh (cheap if within TTL)
#   2. merge Supabase-reconstructed data with in-code fallback via _merge()
#      - fallback fills any gaps (entities not yet seeded to Supabase)
#      - fallback wins on value conflicts (guards against stale Supabase data)
#      - Supabase-only entries (added post-seed) are preserved
# ---------------------------------------------------------------------------

def get_resource_collection_map() -> dict:
    """Return {category: [{display_name: terraform_key}, ...]}."""
    _ensure_fresh()
    d = (_state._data or {}).get("RESOURCE_COLLECTION_MAP")
    return _merge(d, _fb("RESOURCE_COLLECTION_MAP"))


def get_entity_id_mapping() -> dict:
    """Return {display_name: id_key}.

    NOTE: ``terraform_registry.id_key`` was seeded from the OkTf ID_KEYS registry
    (terraform_key-keyed), not from ENTITY_ID_MAPPING (display_name-keyed).  The
    fallback (in-code ENTITY_ID_MAPPING) is therefore the authoritative source for
    most entries; Supabase-only entries are still surfaced via the merge.
    """
    _ensure_fresh()
    d = (_state._data or {}).get("ENTITY_ID_MAPPING")
    return _merge(d, _fb("ENTITY_ID_MAPPING"))


def get_non_editable_fields() -> dict:
    """Return {display_name: [non-editable field, ...]}."""
    _ensure_fresh()
    d = (_state._data or {}).get("NON_EDITABLE_FIELDS")
    return _merge(d, _fb("NON_EDITABLE_FIELDS"))


def get_excluded_output_fields() -> dict:
    """Return {tf_key: [excluded field, ...] or str}."""
    _ensure_fresh()
    d = (_state._data or {}).get("EXCLUDED_OUTPUT_FIELDS")
    return _merge(d, _fb("EXCLUDED_OUTPUT_FIELDS"))


def get_entity_target_field_map() -> dict:
    """Return {tf_key: id_field | [id_field, ...]}."""
    _ensure_fresh()
    d = (_state._data or {}).get("ENTITY_TARGET_FIELD_MAP")
    return _merge(d, _fb("ENTITY_TARGET_FIELD_MAP"))


def get_none_field_lists() -> dict:
    """Return {tf_key: {field: default_value}}."""
    _ensure_fresh()
    d = (_state._data or {}).get("NONE_FIELD_LISTS")
    return _merge(d, _fb("NONE_FIELD_LISTS"))


def get_entity_target_prefix_map() -> dict:
    """Return {tf_key: [target_address, ...]}."""
    _ensure_fresh()
    d = (_state._data or {}).get("ENTITY_TARGET_PREFIX_MAP")
    return _merge(d, _fb("ENTITY_TARGET_PREFIX_MAP"))


def get_entity_type_mapping() -> dict:
    """Return {tf_key: {"okta_endpoint": ..., "attributes": [...]}}."""
    _ensure_fresh()
    d = (_state._data or {}).get("ENTITY_TYPE_MAPPING")
    return _merge(d, _fb("ENTITY_TYPE_MAPPING"))


def get_id_keys() -> dict:
    """Return {tf_key: id_key}."""
    _ensure_fresh()
    d = (_state._data or {}).get("ID_KEYS")
    return _merge(d, _fb("ID_KEYS"))


def get_rules_fields() -> dict:
    """Return {tf_key: rules_field}."""
    _ensure_fresh()
    d = (_state._data or {}).get("RULES_FIELDS")
    return _merge(d, _fb("RULES_FIELDS"))


def get_entity_unique_fields() -> dict:
    """Return {tf_key: unique_key} (terraform_key-keyed)."""
    _ensure_fresh()
    d = (_state._data or {}).get("ENTITY_UNIQUE_FIELDS")
    return _merge(d, _fb("ENTITY_UNIQUE_FIELDS"))


def get_singleton_resource_identifiers() -> dict:
    """Return {tf_key: singleton_identifier}."""
    _ensure_fresh()
    d = (_state._data or {}).get("SINGLETON_RESOURCE_IDENTIFIERS")
    return _merge(d, _fb("SINGLETON_RESOURCE_IDENTIFIERS"))


def get_entity_import_mapping() -> dict:
    """Return {tf_key: {import_address, okta_id_field, ...}}."""
    _ensure_fresh()
    d = (_state._data or {}).get("ENTITY_IMPORT_MAPPING")
    return _merge(d, _fb("ENTITY_IMPORT_MAPPING"))


def get_nested_field_collections() -> dict:
    """Return {display_name: {child_field: child_resource}}."""
    _ensure_fresh()
    d = (_state._data or {}).get("NESTED_FIELD_COLLECTIONS")
    return _merge(d, _fb("NESTED_FIELD_COLLECTIONS"))


def get_nested_field_id_mapping() -> dict:
    """Return {child_field: {parent_id_field, child_id_field}}."""
    _ensure_fresh()
    d = (_state._data or {}).get("NESTED_FIELD_ID_MAPPING")
    return _merge(d, _fb("NESTED_FIELD_ID_MAPPING"))


def get_entities_with_builders() -> list:
    """Return [display_name, ...] of entities that have nested data builders."""
    _ensure_fresh()
    d = (_state._data or {}).get("ENTITIES_WITH_BUILDERS")
    fb = _fb("ENTITIES_WITH_BUILDERS", default=[])
    if not d:
        return fb if fb else []
    # Union: preserve all in-code entries + any Supabase-only entries
    seen = set(d)
    return list(d) + [x for x in (fb or []) if x not in seen]


def get_wrapper_map() -> dict:
    """Return {tf_key: wrapper_key}  (OkTf: ENTITY_FIELD_MAPPING)."""
    _ensure_fresh()
    d = (_state._data or {}).get("WRAPPER_MAP")
    return _merge(d, _fb("WRAPPER_MAP"))


def get_state_file_map() -> dict:
    """Return {tf_key: state_file_path}  (OkTf: COLLECTION_STATE_MAP)."""
    _ensure_fresh()
    d = (_state._data or {}).get("STATE_FILE_MAP")
    return _merge(d, _fb("STATE_FILE_MAP"))


def get_grouped_entities() -> set:
    """Return set of tf_keys that use composite keys  (OkTf: GROUPED_ENTITIES)."""
    _ensure_fresh()
    d = (_state._data or {}).get("GROUPED_ENTITIES")
    fb = _fb("GROUPED_ENTITIES", default=set())
    if d is None:
        return fb if fb else set()
    # Union: Supabase + fallback
    return d | (fb if isinstance(fb, set) else set(fb))


def get_nested_entity_config() -> dict:
    """Return {tf_key: {parent_resource, child_resource|children}}  (OkTf)."""
    _ensure_fresh()
    d = (_state._data or {}).get("NESTED_ENTITY_CONFIG")
    return _merge(d, _fb("NESTED_ENTITY_CONFIG"))


def get_entity_unique_keys() -> dict:
    """Return {wrapper_key: unique_field_name}  (OkTf: ENTITY_UNIQUE_KEYS).

    This flat map ({wrapper_key: "field_str"}) is NOT reconstructible from the
    Supabase nested_entity_mapping table (which stores child-level structures).
    Always defers to the caller-supplied in-code fallback.
    """
    _ensure_fresh()
    return _fb("ENTITY_UNIQUE_KEYS")


def get_base_api_path() -> dict:
    """Return {display_name: base_api_path}."""
    _ensure_fresh()
    d = (_state._data or {}).get("BASE_API_PATH")
    return _merge(d, _fb("BASE_API_PATH"))


def get_model_registry() -> dict:
    """
    Return {display_name: ModelClass}.

    Classes are resolved via importlib from the stored module paths.  Any class
    that cannot be imported falls back to the corresponding in-code registry
    entry (or is omitted if neither source has it).
    """
    _ensure_fresh()
    model_map = (_state._data or {}).get("_MODEL_MAP") or {}
    fallback = _fb("MODEL_REGISTRY")

    if not model_map:
        return fallback

    result: dict = {}
    for display_name, (module_path, class_name) in model_map.items():
        try:
            mod = importlib.import_module(module_path)
            cls = getattr(mod, class_name)
            result[display_name] = cls
        except Exception as exc:
            fb_cls = fallback.get(display_name)
            if fb_cls is not None:
                result[display_name] = fb_cls
            else:
                logger.warning(
                    "[mapping_provider] Cannot import model %s.%s: %s",
                    module_path, class_name, exc,
                )

    # Include any in-code entries not present in Supabase data
    for k, v in fallback.items():
        if k not in result:
            result[k] = v

    return result or fallback


def get_serializer_registry() -> dict:
    """
    Return {display_name: SerializerClass}.

    Same importlib resolution approach as get_model_registry().
    """
    _ensure_fresh()
    serializer_map = (_state._data or {}).get("_SERIALIZER_MAP") or {}
    fallback = _fb("SERIALIZER_REGISTRY")

    if not serializer_map:
        return fallback

    result: dict = {}
    for display_name, (module_path, class_name) in serializer_map.items():
        try:
            mod = importlib.import_module(module_path)
            cls = getattr(mod, class_name)
            result[display_name] = cls
        except Exception as exc:
            fb_cls = fallback.get(display_name)
            if fb_cls is not None:
                result[display_name] = fb_cls
            else:
                logger.warning(
                    "[mapping_provider] Cannot import serializer %s.%s: %s",
                    module_path, class_name, exc,
                )

    for k, v in fallback.items():
        if k not in result:
            result[k] = v

    return result or fallback
