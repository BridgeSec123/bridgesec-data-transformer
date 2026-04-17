import logging
import os
import sys

from dotenv import load_dotenv

# Load .env from repo root (one level up from mcp_server/)
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# Ensure sibling modules (auth, client) are importable
sys.path.insert(0, os.path.dirname(__file__))

import client as api  # noqa: E402 — must come after load_dotenv

from mcp.server.fastmcp import FastMCP  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

READ_ONLY = os.environ.get("MCP_READ_ONLY", "false").lower() == "true"

mcp = FastMCP("bridgesec-data-transformer")


# ─── READ-ONLY TOOLS ──────────────────────────────────────────────────────────

@mcp.tool()
def list_snapshots(date: str = None) -> dict:
    """
    List all available Okta snapshot databases grouped by date.

    Without date: returns all dates with snapshot counts and the full snapshot list per date.
    With date (format DD-MM-YY): returns paginated snapshots for that specific date.

    Use the db_name values returned here as input to get_entity_data, restore_entity, etc.
    """
    params = {"date": date} if date else {}
    return api.get("/db-map/", params=params)


@mcp.tool()
def list_entity_types() -> dict:
    """
    List all supported Okta entity types.

    Returns names like: users, groups, apps_oauth, policy_mfa, auth_server, etc.
    Use these names as the entity_name argument in other tools.
    """
    return api.get("/resources/")


@mcp.tool()
def get_entity_data(db_name: str, entity_name: str, page: int = 1, page_size: int = 20) -> dict:
    """
    Fetch records for a specific Okta entity type from a snapshot database.

    db_name: full snapshot DB name e.g. bridgesec_2026-04-03T0000 — get this from list_snapshots.
    entity_name: entity type e.g. users, groups, policy_mfa — get this from list_entity_types.
    page / page_size: paginate through large result sets.
    """
    return api.get("/data/", params={
        "db_name": db_name,
        "entity_name": entity_name,
        "page": page,
        "page_size": page_size,
    })


@mcp.tool()
def get_entity_schema(entity_name: str) -> dict:
    """
    Get the field schema and metadata for an Okta entity type.

    Returns field names, types, and which fields are non-editable.
    Call this before restore_entity to understand what can be changed.
    """
    return api.get(f"/entity-schema/{entity_name}/")


@mcp.tool()
def diff_snapshots(entity_name: str, db1: str, db2: str) -> dict:
    """
    Compare a specific Okta entity type between two snapshot databases.

    Returns records that were added, removed, or changed between db1 and db2.
    Both db1 and db2 must be full snapshot DB names from list_snapshots.
    """
    return api.get(f"/diff-collections/{entity_name}/", params={"db1": db1, "db2": db2})


# ─── WRITE TOOLS (disabled when MCP_READ_ONLY=true) ──────────────────────────

if not READ_ONLY:

    @mcp.tool()
    def trigger_bulk_fetch() -> dict:
        """
        Trigger a new Okta snapshot. Runs as a background Celery task.

        The new snapshot will appear in list_snapshots once complete (typically a few minutes).
        Returns the Celery task ID for tracking.
        """
        return api.post("/api/bulk/")

    @mcp.tool()
    def restore_entity(db_name: str, entity_name: str, records: list, source_db: str = None) -> dict:
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
        return api.post(f"/restore/{db_name}/{entity_name}/", body=records, params=params)

    @mcp.tool()
    def create_entity(db_name: str, entity_name: str, all_records: list) -> dict:
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
        return api.post(f"/restore/{db_name}/{entity_name}/", body=all_records)

    @mcp.tool()
    def plan_deletion(db_name: str, entity_name: str, records_to_delete: list) -> dict:
        """
        Stage a deletion plan for user review. Nothing is deleted yet.

        Returns a plan_id and a summary of what will be deleted, including any
        cascaded child entities (e.g. deleting a policy also deletes its rules).
        Plans expire after 15 minutes.

        Next steps: call confirm_deletion to execute or cancel_deletion to abort.
        """
        return api.post(
            f"/restore/{db_name}/{entity_name}/",
            body=records_to_delete,
            params={"operation_type": "delete", "phase": "plan"},
        )

    @mcp.tool()
    def confirm_deletion(plan_id: str) -> dict:
        """
        IRREVERSIBLE. Execute a staged deletion plan via Terraform.

        Only call this after the user has explicitly reviewed and approved the deletion
        summary returned by plan_deletion. The plan_id comes from that response.
        Once confirmed, the resources are permanently deleted from Okta.
        """
        return api.post("/confirm-delete/", params={"plan_id": plan_id, "action": "confirm"})

    @mcp.tool()
    def cancel_deletion(plan_id: str) -> dict:
        """
        Cancel a pending deletion plan. No changes are made to Okta.

        Removes all staged records from MongoDB and invalidates the plan_id.
        """
        return api.post("/confirm-delete/", params={"plan_id": plan_id, "action": "deny"})


# ─── ENTRY POINT ─────────────────────────────────────────────────────────────

class HostOverrideMiddleware:
    """Rewrites the Host header to localhost before the MCP transport validates it."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            headers = [
                (b"host", b"localhost") if k == b"host" else (k, v)
                for k, v in scope.get("headers", [])
            ]
            scope["headers"] = headers
        await self.app(scope, receive, send)


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("MCP_PORT", 8002))
    app = mcp.streamable_http_app()
    app = HostOverrideMiddleware(app)
    uvicorn.run(app, host="0.0.0.0", port=port)
