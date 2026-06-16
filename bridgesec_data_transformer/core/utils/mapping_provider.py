"""
mapping_provider.py — Primary-repo thin wrapper around bridgesec_logging.mapping_provider.

This module configures the shared provider with the Django Supabase client and all
in-code mapping registries as fallbacks, then re-exports every accessor so consumer
code can do a single import:

    from core.utils.mapping_provider import (
        get_resource_collection_map,
        get_entity_id_mapping,
        ...
    )

Configuration (configure_mapping_provider) is called once from CoreConfig.ready()
in core/apps.py.  Subsequent accessor calls are O(1) from the TTL cache.
"""

import logging

logger = logging.getLogger(__name__)


def configure_mapping_provider():
    """
    Wire the shared provider to the primary-repo Supabase client and in-code fallbacks.
    Called exactly once from core.apps.CoreConfig.ready().
    """
    from django.conf import settings

    # --- Import all in-code registries (they remain the fallbacks) ---
    from core.utils.collection_mapping import (
        ENTITY_ID_MAPPING,
        NON_EDITABLE_FIELDS,
        RESOURCE_COLLECTION_MAP,
    )
    from core.utils.constants import (
        ENTITY_TARGET_FIELD_MAP,
        SINGLETON_RESOURCE_IDENTIFIERS,
    )
    from core.utils.entity_mapping import (
        ENTITY_IMPORT_MAPPING,
        ENTITY_TARGET_PREFIX_MAP,
        ENTITY_TYPE_MAPPING,
        EXCLUDED_OUTPUT_FIELDS,
    )
    from core.utils.mapping_handlers import (
        ENTITY_UNIQUE_FIELDS,
        ID_KEYS,
        NONE_FIELD_LISTS,
        RULES_FIELDS,
    )
    from core.utils.model_registry import MODEL_REGISTRY
    from core.utils.nested_mapping import (
        ENTITIES_WITH_BUILDERS,
        NESTED_FIELD_COLLECTIONS,
        NESTED_FIELD_ID_MAPPING,
    )
    from core.utils.serializer_registry import SERIALIZER_REGISTRY

    fallbacks = {
        "RESOURCE_COLLECTION_MAP":        RESOURCE_COLLECTION_MAP,
        "ENTITY_ID_MAPPING":              ENTITY_ID_MAPPING,
        "NON_EDITABLE_FIELDS":            NON_EDITABLE_FIELDS,
        "EXCLUDED_OUTPUT_FIELDS":         EXCLUDED_OUTPUT_FIELDS,
        "ENTITY_TARGET_FIELD_MAP":        ENTITY_TARGET_FIELD_MAP,
        "NONE_FIELD_LISTS":               NONE_FIELD_LISTS,
        "ENTITY_TARGET_PREFIX_MAP":       ENTITY_TARGET_PREFIX_MAP,
        "ENTITY_TYPE_MAPPING":            ENTITY_TYPE_MAPPING,
        "ID_KEYS":                        ID_KEYS,
        "RULES_FIELDS":                   RULES_FIELDS,
        "ENTITY_UNIQUE_FIELDS":           ENTITY_UNIQUE_FIELDS,
        "SINGLETON_RESOURCE_IDENTIFIERS": SINGLETON_RESOURCE_IDENTIFIERS,
        "ENTITY_IMPORT_MAPPING":          ENTITY_IMPORT_MAPPING,
        "NESTED_FIELD_COLLECTIONS":       NESTED_FIELD_COLLECTIONS,
        "NESTED_FIELD_ID_MAPPING":        NESTED_FIELD_ID_MAPPING,
        "ENTITIES_WITH_BUILDERS":         ENTITIES_WITH_BUILDERS,
        "MODEL_REGISTRY":                 MODEL_REGISTRY,
        "SERIALIZER_REGISTRY":            SERIALIZER_REGISTRY,
    }

    ttl_sec = getattr(settings, "MAPPINGS_CACHE_TTL_SEC", 300)

    from bridgesec_logging.mapping_provider import configure
    from core.utils.supabase_client import get_supabase_client

    configure(
        client_getter=get_supabase_client,
        fallbacks=fallbacks,
        ttl_sec=ttl_sec,
    )
    logger.info(
        "Mapping provider configured (ttl=%ss, Supabase=%s)",
        ttl_sec,
        "yes" if getattr(settings, "SUPABASE_URL", None) else "no — fallbacks only",
    )


# ---------------------------------------------------------------------------
# Re-export all accessors so consumers can do:
#     from core.utils.mapping_provider import get_resource_collection_map
# ---------------------------------------------------------------------------

from bridgesec_logging.mapping_provider import (  # noqa: E402
    get_base_api_path,
    get_entities_with_builders,
    get_entity_id_mapping,
    get_entity_import_mapping,
    get_entity_target_field_map,
    get_entity_target_prefix_map,
    get_entity_type_mapping,
    get_entity_unique_fields,
    get_entity_unique_keys,
    get_excluded_output_fields,
    get_grouped_entities,
    get_id_keys,
    get_model_registry,
    get_nested_entity_config,
    get_nested_field_collections,
    get_nested_field_id_mapping,
    get_non_editable_fields,
    get_none_field_lists,
    get_resource_collection_map,
    get_rules_fields,
    get_serializer_registry,
    get_singleton_resource_identifiers,
    get_state_file_map,
    get_wrapper_map,
    refresh as refresh_mappings,
)

__all__ = [
    "configure_mapping_provider",
    "refresh_mappings",
    "get_resource_collection_map",
    "get_entity_id_mapping",
    "get_non_editable_fields",
    "get_excluded_output_fields",
    "get_entity_target_field_map",
    "get_none_field_lists",
    "get_entity_target_prefix_map",
    "get_entity_type_mapping",
    "get_id_keys",
    "get_rules_fields",
    "get_entity_unique_fields",
    "get_singleton_resource_identifiers",
    "get_entity_import_mapping",
    "get_nested_field_collections",
    "get_nested_field_id_mapping",
    "get_entities_with_builders",
    "get_model_registry",
    "get_serializer_registry",
    "get_base_api_path",
    "get_entity_target_prefix_map",
    "get_wrapper_map",
    "get_state_file_map",
    "get_grouped_entities",
    "get_nested_entity_config",
    "get_entity_unique_keys",
]
