import logging
import os
import sys

from dotenv import load_dotenv

# Load .env from repo root (one level up from mcp_server/)
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# Ensure sibling modules (client) are importable
sys.path.insert(0, os.path.dirname(__file__))

import client as api  # noqa: E402 — must come after load_dotenv

from mcp.server.fastmcp import Context, FastMCP  # noqa: E402
from mcp.server.transport_security import TransportSecuritySettings  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

READ_ONLY = os.environ.get("MCP_READ_ONLY", "false").lower() == "true"

mcp = FastMCP(
    "bridgesec-data-transformer",
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)


def _caller_token(ctx: Context) -> str:
    """
    Extract the bearer token from the HTTP request that invoked this tool.

    The calling application forwards the logged-in user's token to the MCP
    server; we read it off the incoming request and reuse it verbatim for the
    downstream Django API call. Django then authenticates as that user and
    resolves their tenant from the token's `tenant_id` claim — no service-app
    identity is involved.
    """
    request = getattr(ctx.request_context, "request", None)
    auth = request.headers.get("authorization") if request is not None else None
    if not auth or not auth.lower().startswith("bearer "):
        raise ValueError(
            "Missing or invalid Authorization header. The MCP server requires the "
            "caller to forward the user's bearer token."
        )
    return auth.split(" ", 1)[1].strip()


# ─── READ-ONLY TOOLS ──────────────────────────────────────────────────────────

@mcp.tool()
def list_snapshots(ctx: Context, date: str = None) -> dict:
    """
    List all available Okta snapshot databases grouped by date.

    Without date: returns all dates with snapshot counts and the full snapshot list per date.
    With date (format DD-MM-YY): returns paginated snapshots for that specific date.

    Use the db_name values returned here as input to get_entity_data, restore_entity, etc.
    """
    params = {"date": date} if date else {}
    return api.get("/db-map/", _caller_token(ctx), params=params)


@mcp.tool()
def list_entity_types(ctx: Context) -> dict:
    """
    List all supported Okta entity types.

    Returns names like: users, groups, apps_oauth, policy_mfa, auth_server, etc.
    Use these names as the entity_name argument in other tools.
    """
    return api.get("/resources/", _caller_token(ctx))


@mcp.tool()
def get_entity_data(ctx: Context, db_name: str, entity_name: str, page: int = 1, page_size: int = 20) -> dict:
    """
    Fetch records for a specific Okta entity type from a snapshot database.

    db_name: full snapshot DB name e.g. bridgesec_2026-04-03T0000 — get this from list_snapshots.
    entity_name: entity type e.g. users, groups, policy_mfa — get this from list_entity_types.
    page / page_size: paginate through large result sets.
    """
    return api.get("/data/", _caller_token(ctx), params={
        "db_name": db_name,
        "entity_name": entity_name,
        "page": page,
        "page_size": page_size,
    })


@mcp.tool()
def get_entity_schema(ctx: Context, entity_name: str) -> dict:
    """
    Get the field schema and metadata for an Okta entity type.

    Returns field names, types, and which fields are non-editable.
    Call this before restore_entity to understand what can be changed.
    """
    return api.get(f"/entity-schema/{entity_name}/", _caller_token(ctx))


@mcp.tool()
def diff_snapshots(ctx: Context, entity_name: str, db1: str, db2: str) -> dict:
    """
    Compare a specific Okta entity type between two snapshot databases.

    Returns records that were added, removed, or changed between db1 and db2.
    Both db1 and db2 must be full snapshot DB names from list_snapshots.
    """
    return api.get(f"/diff-collections/{entity_name}/", _caller_token(ctx), params={"db1": db1, "db2": db2})


@mcp.tool()
def get_diff_report(ctx: Context, db_name: str) -> dict:
    """
    Fetch the stored diff summary for a completed snapshot.

    Use this when a bulk fetch's SSE progress stream was closed before the
    `complete` event arrived, or when revisiting a past snapshot later.
    Returns 404 if no diff has run yet for that db_name.
    """
    return api.get(f"/api/diff-report/{db_name}/", _caller_token(ctx))


@mcp.tool()
def list_activity_logs(
    ctx: Context,
    operations_only: bool = False,
    action: str = None,
    actions: str = None,
    user_email: str = None,
    date_from: str = None,
    date_to: str = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """
    List per-tenant activity log entries (bulk fetches, restores, creates, deletes, etc).

    Only available in multi-tenant mode; requires tenant context on the caller's token.
    operations_only: shortcut to only return UI operation actions (bulk_fetch, restore,
        create, delete, compare, migrate) — overrides action/actions if set.
    actions: comma-separated action list, e.g. "bulk_fetch,restore,delete".
    date_from / date_to: ISO 8601 date strings, inclusive.
    """
    params = {
        "operations_only": "true" if operations_only else None,
        "action": action,
        "actions": actions,
        "user_email": user_email,
        "date_from": date_from,
        "date_to": date_to,
        "page": page,
        "page_size": page_size,
    }
    return api.get("/logs/", _caller_token(ctx), params={k: v for k, v in params.items() if v is not None})


@mcp.tool()
def get_scheduler_config(ctx: Context) -> dict:
    """
    Get the caller's tenant scheduled-fetch configuration.

    Returns scheduler_enabled, scheduler_hour, scheduler_minute, scheduler_timezone,
    and which Okta service scopes are granted. In single-tenant mode, returns the
    read-only values from .env (editable=False).
    """
    return api.get("/api/scheduler-config/", _caller_token(ctx))


@mcp.tool()
def get_entity_config(ctx: Context, tenant_id: str = None) -> dict:
    """
    List all backup entities/collections and their enabled status for the caller's tenant.

    Grouped by category. Super admins may pass tenant_id to inspect another tenant's
    config; omitted, they get the global default config.
    """
    params = {"tenant_id": tenant_id} if tenant_id else {}
    return api.get("/api/entity-config/", _caller_token(ctx), params=params)


# ─── WRITE TOOLS (disabled when MCP_READ_ONLY=true) ──────────────────────────

if not READ_ONLY:

    @mcp.tool()
    def trigger_bulk_fetch(ctx: Context) -> dict:
        """
        Trigger a new Okta snapshot. Runs as a background Celery task.

        The new snapshot will appear in list_snapshots once complete (typically a few minutes).
        Returns the Celery task ID for tracking.
        """
        return api.post("/api/bulk/", _caller_token(ctx))

    @mcp.tool()
    def restore_entity(ctx: Context, db_name: str, entity_name: str, records: list, source_db: str = None) -> dict:
        """
        Restore or modify Okta entity records in a snapshot database.

        IMPORTANT: records must contain ALL records for this entity type — not just the changed ones.
        Sending partial data will cause Terraform to delete the omitted records from Okta.

        Recommended flow:
          1. Call get_entity_data to fetch the full current list.
          2. Apply your changes to the returned list.
          3. Pass the complete modified list as records here.

        source_db: optional — if provided, uses a different snapshot as the Terraform merge source
                   while writing to db_name. Useful when restoring from a historical snapshot.
        """
        params = {"source_db": source_db} if source_db else {}
        return api.post(f"/restore/{db_name}/{entity_name}/", _caller_token(ctx), body=records, params=params)

    @mcp.tool()
    def create_entity(ctx: Context, db_name: str, entity_name: str, all_records: list) -> dict:
        """
        Create a new Okta entity of a given type.

        all_records must contain ALL existing records of this entity type PLUS the new record
        appended to the list. The new record must NOT have an ID field — the absence of an ID
        is what signals the backend to treat it as a creation.

        Recommended flow:
          1. Call get_entity_data to fetch all existing records.
          2. Build the new record dict without an id/profile_id/app_id field.
          3. Append it to the existing list and pass the full list as all_records.
        """
        return api.post(f"/restore/{db_name}/{entity_name}/", _caller_token(ctx), body=all_records)

    @mcp.tool()
    def plan_deletion(ctx: Context, db_name: str, entity_name: str, records_to_delete: list) -> dict:
        """
        Stage a deletion plan for user review. Nothing is deleted yet.

        Returns a plan_id and a summary of what will be deleted, including any
        cascaded child entities (e.g. deleting a policy also deletes its rules).
        Plans expire after 15 minutes.

        Next steps: call confirm_deletion to execute or cancel_deletion to abort.
        """
        return api.post(
            f"/restore/{db_name}/{entity_name}/",
            _caller_token(ctx),
            body=records_to_delete,
            params={"operation_type": "delete", "phase": "plan"},
        )

    @mcp.tool()
    def confirm_deletion(ctx: Context, plan_id: str) -> dict:
        """
        IRREVERSIBLE. Execute a staged deletion plan via Terraform.

        Only call this after the user has explicitly reviewed and approved the deletion
        summary returned by plan_deletion. The plan_id comes from that response.
        Once confirmed, the resources are permanently deleted from Okta.
        """
        return api.post("/confirm-delete/", _caller_token(ctx), params={"plan_id": plan_id, "action": "confirm"})

    @mcp.tool()
    def cancel_deletion(ctx: Context, plan_id: str) -> dict:
        """
        Cancel a pending deletion plan. No changes are made to Okta.

        Removes all staged records from MongoDB and invalidates the plan_id.
        """
        return api.post("/confirm-delete/", _caller_token(ctx), params={"plan_id": plan_id, "action": "deny"})

    @mcp.tool()
    def update_scheduler_config(
        ctx: Context,
        scheduler_enabled: bool = None,
        scheduler_hour: int = None,
        scheduler_minute: int = None,
        scheduler_timezone: str = None,
    ) -> dict:
        """
        Update the caller's tenant scheduled-fetch configuration. Multi-tenant mode only.

        Only super_admin/tenant_admin may write. scheduler_minute must be one of
        0, 15, 30, 45 (the scheduler polls every 15 minutes — any other value would
        be configured but never fire). Call get_scheduler_config first to see current values
        and available_timezones.
        """
        body = {
            "scheduler_enabled": scheduler_enabled,
            "scheduler_hour": scheduler_hour,
            "scheduler_minute": scheduler_minute,
            "scheduler_timezone": scheduler_timezone,
        }
        return api.put("/api/scheduler-config/", _caller_token(ctx), body={k: v for k, v in body.items() if v is not None})

    @mcp.tool()
    def update_entity_config(ctx: Context, updates: list) -> dict:
        """
        Enable or disable backup entities/collections for the caller's tenant.

        updates: list of {"name": "<entity_name>", "enabled": true|false} for entity-level
        toggles, or {"name": "<entity_name>", "collection": "<collection_name>", "enabled": true|false}
        for a single collection within an entity. A collection can only be enabled if its
        parent entity is already enabled. Call get_entity_config first to see valid names.
        """
        return api.put("/api/entity-config/", _caller_token(ctx), body=updates)


# ─── ENTRY POINT ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("MCP_PORT", 8002))
    app = mcp.streamable_http_app()
    uvicorn.run(app, host="0.0.0.0", port=port)
