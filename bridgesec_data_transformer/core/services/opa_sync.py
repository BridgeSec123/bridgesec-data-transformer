import logging

from core.models.policy_models import PolicyRule
from core.services import opa_client, rego_builder

logger = logging.getLogger(__name__)


def sync_from_mongo() -> dict:
    """Push all PolicyRule docs from Mongo to OPA. Idempotent.

    - Always (re)pushes the base aggregation policy under id "base".
    - Pushes each PolicyRule's rego_source under its policy_id.
    - Removes orphaned policies (present in OPA but not in Mongo).
    """
    # Snapshot current OPA state. If OPA is unreachable, bail out gracefully.
    try:
        current_ids = set(opa_client.list_policies())
    except Exception as e:
        logger.warning(
            "OPA unreachable during sync; skipping",
            extra={"component": "opa", "error": str(e)},
        )
        return {"synced": 0, "removed_orphans": 0, "skipped": True}

    # Always push base policy
    opa_client.push_policy("base", rego_builder.BASE_REGO)

    # Push every policy currently stored in Mongo
    pushed = []
    mongo_ids = {"base"}
    for rule in PolicyRule.objects.all():
        rego_text = rule.rego_source or rego_builder.translate(rule)
        opa_client.push_policy(rule.policy_id, rego_text)
        pushed.append(rule.policy_id)
        mongo_ids.add(rule.policy_id)

    # Remove orphans
    orphans = current_ids - mongo_ids
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
        extra={
            "component": "opa",
            "synced": len(pushed),
            "removed_orphans": len(orphans),
        },
    )
    return {"synced": len(pushed), "removed_orphans": len(orphans), "skipped": False}
