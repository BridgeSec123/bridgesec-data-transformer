import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

BASE_URL = settings.BRIDGESEC_API_URL.rstrip("/")

# ─── TOOL DEFINITIONS ────────────────────────────────────────────────────────
# Structured as Anthropic API tool format (input_schema instead of inputSchema).
# Keep in sync with mcp_server/server.py tool descriptions.

READ_TOOLS = [
    {
        "name": "list_snapshots",
        "description": (
            "List all available Okta snapshot databases grouped by date. "
            "Without date: returns all dates with snapshot counts. "
            "With date (DD-MM-YY): returns paginated snapshots for that date. "
            "Use the returned db_name values in other tools."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "Optional date filter in DD-MM-YY format",
                }
            },
        },
    },
    {
        "name": "list_entity_types",
        "description": (
            "List all supported Okta entity types such as users, groups, "
            "apps_oauth, policy_mfa, auth_server, etc. "
            "Use these names as entity_name in other tools."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "get_entity_data",
        "description": (
            "Fetch records for a specific Okta entity type from a snapshot database. "
            "db_name must be the full snapshot DB name e.g. bridgesec_2026-04-07T0000 "
            "— get this from list_snapshots. "
            "Use page and page_size to paginate through large result sets."
        ),
        "input_schema": {
            "type": "object",
            "required": ["db_name", "entity_name"],
            "properties": {
                "db_name": {
                    "type": "string",
                    "description": "Full snapshot DB name e.g. bridgesec_2026-04-07T0000",
                },
                "entity_name": {
                    "type": "string",
                    "description": "Entity type e.g. users, groups, policy_mfa",
                },
                "page": {"type": "integer", "default": 1},
                "page_size": {"type": "integer", "default": 20},
            },
        },
    },
    {
        "name": "get_entity_schema",
        "description": (
            "Get the field schema and metadata for an Okta entity type. "
            "Returns field names, types, and which fields are non-editable. "
            "Call this before restore_entity to understand what can be changed."
        ),
        "input_schema": {
            "type": "object",
            "required": ["entity_name"],
            "properties": {
                "entity_name": {"type": "string"},
            },
        },
    },
    {
        "name": "diff_snapshots",
        "description": (
            "Compare a specific Okta entity type between two snapshot databases. "
            "Returns records that were added, removed, or changed between db1 and db2."
        ),
        "input_schema": {
            "type": "object",
            "required": ["entity_name", "db1", "db2"],
            "properties": {
                "entity_name": {"type": "string"},
                "db1": {"type": "string", "description": "First snapshot DB name"},
                "db2": {"type": "string", "description": "Second snapshot DB name"},
            },
        },
    },
]

WRITE_TOOLS = [
    {
        "name": "trigger_bulk_fetch",
        "description": (
            "Trigger a new Okta snapshot. Runs as a background Celery task. "
            "The new snapshot appears in list_snapshots when complete (a few minutes)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "restore_entity",
        "description": (
            "Restore or modify Okta entity records in a snapshot database. "
            "IMPORTANT: records must contain ALL records for this entity type — not just changed ones. "
            "Sending partial data will cause Terraform to delete the omitted records from Okta. "
            "Recommended flow: call get_entity_data first, modify the list, pass the full list here."
        ),
        "input_schema": {
            "type": "object",
            "required": ["db_name", "entity_name", "records"],
            "properties": {
                "db_name": {"type": "string"},
                "entity_name": {"type": "string"},
                "records": {
                    "type": "array",
                    "description": "Full list of ALL records for this entity type",
                },
                "source_db": {
                    "type": "string",
                    "description": "Optional: use a different snapshot as Terraform merge source",
                },
            },
        },
    },
    {
        "name": "plan_deletion",
        "description": (
            "Stage a deletion plan for user review. Nothing is deleted yet. "
            "Returns a plan_id and summary of what will be deleted including cascaded children. "
            "Plans expire after 15 minutes. "
            "Always show the plan summary to the user and ask for explicit confirmation before calling confirm_deletion."
        ),
        "input_schema": {
            "type": "object",
            "required": ["db_name", "entity_name", "records_to_delete"],
            "properties": {
                "db_name": {"type": "string"},
                "entity_name": {"type": "string"},
                "records_to_delete": {"type": "array"},
            },
        },
    },
    {
        "name": "confirm_deletion",
        "description": (
            "IRREVERSIBLE. Executes a staged deletion plan via Terraform. "
            "Only call this after the user has explicitly reviewed and approved the "
            "plan summary returned by plan_deletion. "
            "The plan_id comes from the plan_deletion response."
        ),
        "input_schema": {
            "type": "object",
            "required": ["plan_id"],
            "properties": {
                "plan_id": {"type": "string"},
            },
        },
    },
    {
        "name": "cancel_deletion",
        "description": (
            "Cancel a pending deletion plan. No changes are made to Okta. "
            "Removes staged records from MongoDB and invalidates the plan_id."
        ),
        "input_schema": {
            "type": "object",
            "required": ["plan_id"],
            "properties": {
                "plan_id": {"type": "string"},
            },
        },
    },
]


def get_tools_for_user(user) -> list:
    """
    Return the tool list scoped to the user's role.
    - admin / superadmin : read + write tools
    - viewer / any other : read-only tools
    """
    role = getattr(user, "role", "viewer")
    if role in ("admin", "superadmin"):
        return READ_TOOLS + WRITE_TOOLS
    return list(READ_TOOLS)


def execute_tool(tool_name: str, tool_input: dict, user_token: str) -> dict:
    """
    Execute a tool by calling the corresponding Django REST endpoint.

    Uses the authenticated USER's Bearer token for every call — never the
    service token. This ensures:
    - Data is scoped to the user's tenant (tenant_id in JWT)
    - Role-based access is enforced by existing Django auth middleware
    - Audit trail is tied to the actual user
    """
    headers = {
        "Authorization": f"Bearer {user_token}",
        "Content-Type": "application/json",
    }

    logger.info(f"Executing tool '{tool_name}' with input keys: {list(tool_input.keys())}")

    match tool_name:
        case "list_snapshots":
            params = {"date": tool_input["date"]} if tool_input.get("date") else {}
            return _get("/db-map/", headers, params=params)

        case "list_entity_types":
            return _get("/resources/", headers)

        case "get_entity_data":
            return _get("/data/", headers, params={
                "db_name": tool_input["db_name"],
                "entity_name": tool_input["entity_name"],
                "page": tool_input.get("page", 1),
                "page_size": tool_input.get("page_size", 20),
            })

        case "get_entity_schema":
            return _get(f"/entity-schema/{tool_input['entity_name']}/", headers)

        case "diff_snapshots":
            return _get(
                f"/diff-collections/{tool_input['entity_name']}/",
                headers,
                params={"db1": tool_input["db1"], "db2": tool_input["db2"]},
            )

        case "trigger_bulk_fetch":
            return _post("/api/bulk/", headers)

        case "restore_entity":
            params = {"source_db": tool_input["source_db"]} if tool_input.get("source_db") else {}
            return _post(
                f"/restore/{tool_input['db_name']}/{tool_input['entity_name']}/",
                headers,
                body=tool_input["records"],
                params=params,
            )

        case "plan_deletion":
            return _post(
                f"/restore/{tool_input['db_name']}/{tool_input['entity_name']}/",
                headers,
                body=tool_input["records_to_delete"],
                params={"operation_type": "delete", "phase": "plan"},
            )

        case "confirm_deletion":
            return _post(
                "/confirm-delete/",
                headers,
                params={"plan_id": tool_input["plan_id"], "action": "confirm"},
            )

        case "cancel_deletion":
            return _post(
                "/confirm-delete/",
                headers,
                params={"plan_id": tool_input["plan_id"], "action": "deny"},
            )

        case _:
            logger.warning(f"Unknown tool requested: {tool_name}")
            return {"error": f"Unknown tool: {tool_name}"}


# ─── HTTP HELPERS ─────────────────────────────────────────────────────────────

def _get(path: str, headers: dict, params: dict = None) -> dict:
    resp = requests.get(f"{BASE_URL}{path}", headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _post(path: str, headers: dict, body=None, params: dict = None) -> dict:
    resp = requests.post(
        f"{BASE_URL}{path}",
        headers=headers,
        json=body or {},
        params=params,
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()
