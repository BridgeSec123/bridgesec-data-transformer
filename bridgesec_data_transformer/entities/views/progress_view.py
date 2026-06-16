import json
import logging

from django.conf import settings
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.authentication import CustomJWTAuthentication
from core.services.bulk_progress_stream_service import BulkProgressStreamService
from core.utils.progress_store import get_bulk_job
from core.utils.sse_helpers import sse_event, make_sse_response
from entities.services.SupabasePopulateService import SupabaseStateBackend
logger = logging.getLogger(__name__)


def _resolve_progress_mongo_uri(request) -> str:
    """
    Return the tenant's mongo_uri so progress reads hit the same cluster that
    the write path (bulk_view + worker) used.  Falls back to None, which makes
    progress_store use the system-level client (single-tenant path).
    """
    try:
        from core.utils.tenant_utils import resolve_tenant_for_request, get_mongo_client_for_tenant
        tenant = resolve_tenant_for_request(request)
        if tenant and tenant.mongo_uri:
            return tenant.mongo_uri
    except Exception:
        pass
    return getattr(request, "_mongo_uri", None)


class BulkProgressView(APIView):
    """
    GET /api/bulk/progress/?request_id=<uuid>

    One-shot JSON poll that returns the current state of a bulk-fetch job.
    Returns the full job document with a `progress_pct` field added.
    """
    authentication_classes = [CustomJWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Poll the current progress of a bulk-fetch job",
        manual_parameters=[
            openapi.Parameter(
                "request_id", openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="The request_id returned by POST /api/bulk/",
                required=True,
            )
        ],
        responses={
            200: "Job progress document",
            400: "Missing request_id",
            404: "Job not found",
        },
        tags=["bulk"],
    )
    def get(self, request):
        request_id = request.query_params.get("request_id")
        if not request_id:
            return Response(
                {"error": "Missing required query parameter: request_id"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        mongo_uri = _resolve_progress_mongo_uri(request)
        job = get_bulk_job(request_id, mongo_uri=mongo_uri)
        if job is None:
            return Response(
                {"error": f"Job '{request_id}' not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        job["_id"] = str(job["_id"])
        total = job.get("total") or 1
        completed = job.get("completed", 0)
        job["progress_pct"] = round(completed / total * 100)

        return Response(job, status=status.HTTP_200_OK)


class BulkProgressStreamView(APIView):
    """
    GET /api/bulk/progress/stream/?request_id=<uuid>

    Server-Sent Events stream for real-time bulk-fetch progress.

    Emits a `data:` event every ~2 seconds while the job is running,
    then a named `event: complete` event once the job finishes (status
    becomes "completed" or "failed").  The stream closes after the
    terminal event.

    Event types:
    - (unnamed)      — progress tick with full job doc + progress_pct
    - complete       — terminal event; job doc includes diff_summary
    - heartbeat      — `: ping` comment (keep-alive)
    - error          — job not found or stream setup error
    """
    authentication_classes = [CustomJWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="SSE stream of bulk-fetch progress; terminates with a 'complete' event carrying the diff summary",
        manual_parameters=[
            openapi.Parameter(
                "request_id", openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="The request_id returned by POST /api/bulk/",
                required=True,
            )
        ],
        responses={200: "SSE stream", 400: "Missing request_id"},
        tags=["bulk"],
    )
    def get(self, request):
        request_id = request.query_params.get("request_id")
        if not request_id:
            return Response(
                {"error": "Missing required query parameter: request_id"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        mongo_uri = _resolve_progress_mongo_uri(request)
        service = BulkProgressStreamService(request_id, mongo_uri=mongo_uri)

        def _generator():
            for event in service.stream():
                event_type = event["type"]
                if event_type == "progress":
                    yield sse_event(json.dumps(event["data"]))
                elif event_type == "complete":
                    yield sse_event(json.dumps(event["data"]), event="complete")
                    return
                elif event_type == "heartbeat":
                    yield ": ping\n\n"
                elif event_type == "error":
                    yield sse_event(json.dumps({"error": event["error"]}), event="error")
                    return

        return make_sse_response(_generator())


class SupabasePopulateView(APIView):
    """
    POST /api/supabase_populate/

    Populates the consolidated Supabase mapping schema from this project's
    in-code registries plus the OkTfModules mappings (core/utils/oktf_mappings.py).

    Tables populated, in dependency order (registry first; the rest FK to it,
    except parent_entity_mapping which is key-based / FK-free):
      1. terraform_registry           — entity master: scalars + folded import + aliases
      2. entity_field_rule            — non_editable / excluded_output / target_id / default
      3. okta_endpoint_attribute      — attributes extracted per Okta endpoint
      4. terraform_target             — Terraform module target addresses (list)
      5. nested_entity_mapping        — parent/child nested-field topology + resource addresses
      6. entity_dependency            — cascade-delete dependency graph
      7. parent_entity_mapping        — app parent/child fetch routing

    Each step runs independently — a failure in one is reported but does not
    abort the others. Response includes per-step status and a final summary.

    Status codes:
      200 — all 7 tables populated successfully
      207 — partial success (at least one step failed)
      502 — every step failed (typically Supabase unreachable / misconfigured)
    """
    authentication_classes = [CustomJWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    # Registry MUST run first — every dependent populator joins against
    # terraform_registry.id, so the table needs rows before the rest can resolve FKs.
    # (parent_entity_mapping is key-based and FK-free, so order-independent.)
    _POPULATE_STEPS = [
        ("terraform_registry",      "populate_terraform_registry"),
        ("entity_field_rule",       "populate_entity_field_rule"),
        ("okta_endpoint_attribute", "populate_okta_endpoint_attribute"),
        ("terraform_target",        "populate_terraform_target"),
        ("nested_entity_mapping",   "populate_nested_entity_mapping"),
        ("entity_dependency",       "populate_entity_dependency"),
        ("parent_entity_mapping",   "populate_parent_entity_mapping"),
    ]

    @swagger_auto_schema(
        operation_description=(
            "Populate the 7 Supabase mapping tables from in-code registries. "
            "Runs each step independently and reports per-step status."
        ),
        responses={
            200: "All tables populated successfully",
            207: "Partial success — some tables failed (see per-step status)",
            502: "All steps failed — Supabase unreachable or misconfigured",
        },
        tags=["supabase"],
    )
    def post(self, request):
        try:
            supabase = SupabaseStateBackend()
        except Exception as exc:
            logger.exception("Failed to initialize SupabaseStateBackend")
            return Response(
                {
                    "status": "failed",
                    "error":  f"Failed to initialize Supabase client: {exc}",
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        steps_result = {}
        successful   = 0
        failed       = 0

        for step_key, method_name in self._POPULATE_STEPS:
            try:
                response = getattr(supabase, method_name)()
                record_count = (
                    len(response.data)
                    if response is not None and getattr(response, "data", None)
                    else 0
                )
                steps_result[step_key] = {
                    "status":  "success",
                    "records": record_count,
                }
                successful += 1
                logger.info(
                    f"[POPULATE OK] {step_key}: {record_count} record(s) upserted",
                    extra={"operation": "Populate Supabase", "step": step_key},
                )
            except Exception as exc:
                failed += 1
                steps_result[step_key] = {
                    "status": "failed",
                    "error":  f"{type(exc).__name__}: {exc}",
                }
                logger.exception(
                    f"[POPULATE FAIL] {step_key}",
                    extra={"operation": "Populate Supabase", "step": step_key},
                )

        total = len(self._POPULATE_STEPS)
        if failed == 0:
            overall_status = "success"
            http_status    = status.HTTP_200_OK
        elif successful == 0:
            overall_status = "failed"
            http_status    = status.HTTP_502_BAD_GATEWAY
        else:
            overall_status = "partial_success"
            http_status    = status.HTTP_207_MULTI_STATUS

        return Response(
            {
                "status":  overall_status,
                "summary": {
                    "total":      total,
                    "successful": successful,
                    "failed":     failed,
                },
                "steps":   steps_result,
            },
            status=http_status,
        )

class DiffReportView(APIView):
    """
    GET /api/diff-report/<db_name>/

    Returns the diff summary document stored in `<db_name>._diff_report`
    after a bulk fetch completes.

    Use this endpoint when:
    - The SSE stream was closed before the `complete` event arrived
    - The user navigates back to a previous snapshot later

    Returns 404 if the diff has not run yet for that snapshot, or the
    snapshot DB does not exist.
    """
    authentication_classes = [CustomJWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Fetch the diff summary for a completed snapshot",
        responses={
            200: "Diff summary document",
            404: "Diff report not available",
        },
        tags=["bulk"],
    )
    def get(self, request, db_name):
        from core.utils.tenant_utils import resolve_tenant_for_request, get_mongo_client_for_tenant, get_request_mongo_client

        # Step 1: resolve the Mongo client — surface connection/config errors as 500.
        # Use resolve_tenant_for_request so super admins with ?tenant_id= query param
        # get the correct tenant's cluster instead of their JWT-scoped default.
        try:
            tenant = resolve_tenant_for_request(request)
            mongo_client = get_mongo_client_for_tenant(tenant) if tenant else get_request_mongo_client(request)
        except Exception as exc:
            logger.exception(
                "Failed to resolve MongoDB client for diff report",
                extra={"component": "api", "db_name": db_name, "error": str(exc)},
            )
            return Response(
                {"error": f"MongoDB connection failed: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Step 2: read the document — surface query errors as 500, missing doc as 404.
        try:
            summary = mongo_client[db_name]["_diff_report"].find_one({"_id": "summary"})
        except Exception as exc:
            logger.exception(
                "Error reading _diff_report from MongoDB",
                extra={"component": "api", "db_name": db_name, "error": str(exc)},
            )
            return Response(
                {"error": f"Failed to read diff report from '{db_name}': {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if summary is None:
            return Response(
                {"error": f"Diff report not available for '{db_name}'"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Strip MongoDB-internal fields before returning
        for field in ("_id", "type", "request_id"):
            summary.pop(field, None)

        return Response(summary, status=status.HTTP_200_OK)
