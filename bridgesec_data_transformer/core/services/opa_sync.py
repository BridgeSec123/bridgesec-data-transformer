import logging

from core.services import opa_client, rego_builder

logger = logging.getLogger(__name__)


def sync_from_mongo() -> dict:
    """Push all PolicyRule rows from Supabase to OPA. Idempotent.

    - Always (re)pushes the base aggregation policy under id "base".
    - Pushes each rule's rego_source under its id (UUID).
    - Removes orphaned policies (present in OPA but not in Supabase).
    """
    try:
        current_ids = set(opa_client.list_policies())
    except Exception as e:
        logger.warning(
            "OPA unreachable during sync; skipping",
            extra={"component": "opa", "error": str(e)},
        )
        return {"synced": 0, "removed_orphans": 0, "skipped": True}

    opa_client.push_policy("base", rego_builder.BASE_REGO)

    from core.utils.supabase_policy import SupabasePolicyRule
    pushed = []
    supabase_ids = {"base"}
    for raw in SupabasePolicyRule.list_all_raw():
        rule = SupabasePolicyRule(raw)
        rego_text = rule.rego_source or rego_builder.translate(rule)
        opa_client.push_policy(str(rule.id), rego_text)
        pushed.append(str(rule.id))
        supabase_ids.add(str(rule.id))

    orphans = current_ids - supabase_ids
    for pid in orphans:
        try:
            opa_client.delete_policy(pid)
        except Exception as e:
            logger.warning(
                "Failed to delete orphan OPA policy",
                extra={"component": "opa", "policy_id": pid, "error": str(e)},
            )

    logger.info(
        "OPA sync complete",
        extra={"component": "opa", "synced": len(pushed), "removed_orphans": len(orphans)},
    )
    return {"synced": len(pushed), "removed_orphans": len(orphans), "skipped": False}
