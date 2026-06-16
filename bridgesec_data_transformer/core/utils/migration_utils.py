import copy
import logging

logger = logging.getLogger(__name__)


def strip_entity_ids(entity_name, records):
    """
    Strip Okta-issued IDs from records so they are treated as new creates
    when submitted to the Terraform pipeline.

    Returns (stripped_records, warnings):
      - stripped_records: deep-copy of records with primary + nested child IDs removed
      - warnings: list of cross-reference _id fields that still remain and may be
                  tenant-specific (e.g. group_id inside a policy condition)
    """
    from core.utils.mapping_provider import get_entity_id_mapping, get_nested_field_collections
    from core.utils.nested_mapping import NESTED_FIELD_ID_MAPPING

    id_field = get_entity_id_mapping().get(entity_name)
    nested_field_collections = get_nested_field_collections().get(entity_name, {})

    stripped = copy.deepcopy(records)
    warnings = []

    for record in stripped:
        # Strip primary entity ID
        if id_field:
            record.pop(id_field, None)

        # Strip nested child/parent IDs for entities with builder collections
        for nested_field_name in nested_field_collections:
            nested_id_info = NESTED_FIELD_ID_MAPPING.get(nested_field_name, {})
            child_id_field = nested_id_info.get("child_id_field")
            parent_id_field = nested_id_info.get("parent_id_field")

            for child in record.get(nested_field_name, []):
                if isinstance(child, dict):
                    if child_id_field:
                        child.pop(child_id_field, None)
                    if parent_id_field:
                        child.pop(parent_id_field, None)

        # Collect cross-reference warnings for remaining _id fields
        skip_fields = {id_field} if id_field else set()
        for key, val in record.items():
            if key.endswith("_id") and key not in skip_fields and val:
                msg = (
                    f"Field '{key}' contains a reference ID from the source tenant — "
                    f"verify it exists in the target tenant before migrating dependent entities."
                )
                if msg not in warnings:
                    warnings.append(msg)

    return stripped, warnings
