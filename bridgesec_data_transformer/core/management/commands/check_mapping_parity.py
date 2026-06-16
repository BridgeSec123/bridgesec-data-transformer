"""
check_mapping_parity.py — Compare Supabase-reconstructed registries against in-code dicts.

Run this after every ``manage.py supabase_populate`` or ``seed_entity_catalog`` to confirm
the live Supabase tables round-trip back to the same data the in-code registries contain.

Usage:
    python manage.py check_mapping_parity             # compare all registries
    python manage.py check_mapping_parity --registry entity_id_mapping
    python manage.py check_mapping_parity --verbose   # print full diff values
    python manage.py check_mapping_parity --refresh   # force cache invalidation first
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Compare Supabase-reconstructed mapping registries against in-code dicts."

    def add_arguments(self, parser):
        parser.add_argument(
            "--registry",
            metavar="NAME",
            help=(
                "Only check one registry by name (e.g. entity_id_mapping, "
                "resource_collection_map, non_editable_fields, …). "
                "Defaults to all registries."
            ),
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Print full expected/actual values for each mismatch.",
        )
        parser.add_argument(
            "--refresh",
            action="store_true",
            help="Invalidate the in-memory cache before checking (forces a fresh Supabase fetch).",
        )

    # -------------------------------------------------------------------------

    def handle(self, *args, **options):
        from bridgesec_logging.mapping_provider import refresh as _refresh
        from core.utils.mapping_provider import (
            get_entities_with_builders,
            get_entity_id_mapping,
            get_entity_target_field_map,
            get_entity_target_prefix_map,
            get_id_keys,
            get_model_registry,
            get_nested_field_collections,
            get_nested_field_id_mapping,
            get_non_editable_fields,
            get_none_field_lists,
            get_resource_collection_map,
            get_serializer_registry,
        )
        # In-code source-of-truth
        from core.utils.collection_mapping import (
            ENTITY_ID_MAPPING,
            NON_EDITABLE_FIELDS,
            RESOURCE_COLLECTION_MAP,
        )
        from core.utils.constants import ENTITY_TARGET_FIELD_MAP
        from core.utils.entity_mapping import ENTITY_TARGET_PREFIX_MAP
        from core.utils.mapping_handlers import ID_KEYS, NONE_FIELD_LISTS
        from core.utils.model_registry import MODEL_REGISTRY
        from core.utils.nested_mapping import (
            ENTITIES_WITH_BUILDERS,
            NESTED_FIELD_COLLECTIONS,
            NESTED_FIELD_ID_MAPPING,
        )
        from core.utils.serializer_registry import SERIALIZER_REGISTRY

        if options["refresh"]:
            _refresh()
            self.stdout.write("Cache invalidated — fetching fresh data from Supabase.")

        verbose = options["verbose"]
        target = options.get("registry")

        # Build registry suite
        #   name → (accessor_fn, in_code_dict, compare_mode)
        #   compare_mode: "dict_keys" | "dict_full" | "list_set"
        SUITE = {
            "resource_collection_map": (
                get_resource_collection_map,
                RESOURCE_COLLECTION_MAP,
                "dict_full",
            ),
            "entity_id_mapping": (
                get_entity_id_mapping,
                ENTITY_ID_MAPPING,
                "dict_full",
            ),
            "non_editable_fields": (
                get_non_editable_fields,
                NON_EDITABLE_FIELDS,
                "dict_full",
            ),
            "entity_target_field_map": (
                get_entity_target_field_map,
                ENTITY_TARGET_FIELD_MAP,
                "dict_full",
            ),
            "entity_target_prefix_map": (
                get_entity_target_prefix_map,
                ENTITY_TARGET_PREFIX_MAP,
                "dict_full",
            ),
            "id_keys": (
                get_id_keys,
                ID_KEYS,
                "dict_full",
            ),
            "none_field_lists": (
                get_none_field_lists,
                {k: (list(v) if isinstance(v, set) else v) for k, v in NONE_FIELD_LISTS.items()},
                "dict_keys",  # values are complex dicts/sets — just check the top-level keys
            ),
            "nested_field_collections": (
                get_nested_field_collections,
                NESTED_FIELD_COLLECTIONS,
                "dict_full",
            ),
            "nested_field_id_mapping": (
                get_nested_field_id_mapping,
                NESTED_FIELD_ID_MAPPING,
                "dict_full",
            ),
            "entities_with_builders": (
                get_entities_with_builders,
                ENTITIES_WITH_BUILDERS,
                "list_set",
            ),
            "model_registry_keys": (
                lambda: list(get_model_registry().keys()),
                list(MODEL_REGISTRY.keys()),
                "list_set",
            ),
            "serializer_registry_keys": (
                lambda: list(get_serializer_registry().keys()),
                list(SERIALIZER_REGISTRY.keys()),
                "list_set",
            ),
        }

        if target:
            if target not in SUITE:
                self.stderr.write(
                    self.style.ERROR(
                        f"Unknown registry '{target}'. Available: {', '.join(sorted(SUITE))}"
                    )
                )
                return
            suite = {target: SUITE[target]}
        else:
            suite = SUITE

        total_issues = 0

        for name, (accessor_fn, expected, mode) in suite.items():
            self.stdout.write(f"\n{'-' * 60}")
            self.stdout.write(f"  {name}")
            self.stdout.write(f"{'-' * 60}")
            try:
                actual = accessor_fn()
            except Exception as exc:
                self.stderr.write(self.style.ERROR(f"  ERROR calling accessor: {exc}"))
                total_issues += 1
                continue

            issues = _compare(name, actual, expected, mode, verbose, self.stdout, self.style)
            total_issues += issues
            if issues == 0:
                self.stdout.write(self.style.SUCCESS("  OK MATCH"))

        self.stdout.write(f"\n{'=' * 60}")
        if total_issues == 0:
            self.stdout.write(self.style.SUCCESS(f"  ALL REGISTRIES MATCH — {len(suite)} checked"))
        else:
            self.stderr.write(
                self.style.ERROR(f"  {total_issues} issue(s) found across {len(suite)} registries")
            )
            raise SystemExit(1)


# ---------------------------------------------------------------------------
# Comparison helpers
# ---------------------------------------------------------------------------

def _compare(name, actual, expected, mode, verbose, stdout, style):
    """Return the number of issues found."""
    issues = 0

    if mode == "list_set":
        actual_set = set(actual) if not isinstance(actual, set) else actual
        expected_set = set(expected) if not isinstance(expected, set) else expected
        missing = expected_set - actual_set
        extra = actual_set - expected_set
        if missing:
            issues += 1
            stdout.write(style.WARNING(f"  MISSING from merged result ({len(missing)}): {sorted(missing)[:20]}"))
        if extra:
            # EXTRA means Supabase has entries the in-code fallback doesn't — informational only
            stdout.write(style.SUCCESS(f"  INFO: EXTRA Supabase-only entries ({len(extra)}): {sorted(extra)[:20]}"))
        return issues

    if mode in ("dict_keys", "dict_full"):
        if not isinstance(actual, dict):
            stdout.write(style.ERROR(f"  Expected dict, got {type(actual).__name__}"))
            return 1
        actual_keys = set(actual.keys())
        expected_keys = set(expected.keys())
        missing = expected_keys - actual_keys
        extra = actual_keys - expected_keys
        if missing:
            issues += 1
            stdout.write(style.WARNING(f"  MISSING keys ({len(missing)}): {sorted(missing)[:20]}"))
        if extra:
            # EXTRA = Supabase-only entries not in in-code fallback — informational, not an error
            stdout.write(style.SUCCESS(f"  INFO: EXTRA Supabase-only keys ({len(extra)}): {sorted(extra)[:20]}"))

    if mode == "dict_full":
        common_keys = set(actual.keys()) & set(expected.keys())
        value_mismatches = []
        for k in sorted(common_keys):
            a_val = actual[k]
            e_val = expected[k]
            if not _deep_eq(a_val, e_val):
                value_mismatches.append(k)
                if verbose:
                    stdout.write(style.WARNING(f"  VALUE MISMATCH  key={k!r}"))
                    stdout.write(f"    expected: {e_val!r}")
                    stdout.write(f"    actual:   {a_val!r}")

        if value_mismatches:
            issues += 1
            if not verbose:
                stdout.write(
                    style.WARNING(
                        f"  VALUE MISMATCH on {len(value_mismatches)} key(s): "
                        f"{sorted(value_mismatches)[:20]}  (use --verbose for details)"
                    )
                )

    return issues


def _deep_eq(a, b):
    """Recursive equality that normalises sets↔lists and dict key ordering."""
    if type(a) != type(b):
        # Tolerate list vs set / tuple interop
        if isinstance(a, (list, set, tuple)) and isinstance(b, (list, set, tuple)):
            return sorted(str(x) for x in a) == sorted(str(x) for x in b)
        return False
    if isinstance(a, dict):
        if a.keys() != b.keys():
            return False
        return all(_deep_eq(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)):
        if len(a) != len(b):
            return False
        return all(_deep_eq(x, y) for x, y in zip(a, b))
    return a == b
