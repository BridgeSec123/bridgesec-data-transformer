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

logger = logging.getLogger(__name__)


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

        job = get_bulk_job(request_id)
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

        service = BulkProgressStreamService(request_id)

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
        try:
            mongo_client = settings.MONGO_CLIENT
            summary = mongo_client[db_name]["_diff_report"].find_one({"_id": "summary"})
        except Exception as exc:
            logger.exception(
                "Error reading _diff_report from MongoDB",
                extra={"component": "api", "db_name": db_name, "error": str(exc)},
            )
            return Response(
                {"error": f"Diff report not available for '{db_name}'"},
                status=status.HTTP_404_NOT_FOUND,
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
