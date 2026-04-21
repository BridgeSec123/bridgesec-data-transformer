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
from core.services.log_stream_service import LogStreamService
from core.utils.sse_helpers import sse_event, make_sse_response
from core.utils.es_client import get_es_client, ConnectionError as ESConnectionError, RequestError as ESRequestError
from core.utils.es_query_builder import (
    INDEX_PATTERN,
    build_log_query,
    build_summary_query,
    build_request_trace_query,
)
from core.serializers.log_serializer import LogQueryParamsSerializer, LogEntrySerializer

logger = logging.getLogger(__name__)


def _hit_to_dict(hit: dict) -> dict:
    """Flatten an ES search hit into the shape LogEntrySerializer expects."""
    doc = hit.get("_source", {})
    doc["_id"] = hit.get("_id")
    # Normalise both timestamp field names Filebeat may produce
    if "@timestamp" in doc and "timestamp" not in doc:
        doc["timestamp"] = doc["@timestamp"]
    return doc


def _sse_generator(log_service: LogStreamService):
    """
    Transport adapter: converts LogStreamService events to SSE format.

    This is the ONLY place that knows about SSE.
    Future transports (WebSocket, gRPC) would have their own adapter.

    Args:
        log_service: LogStreamService instance

    Yields:
        SSE-formatted strings ready to send to client
    """
    for event in log_service.poll_logs():
        if event["type"] == "log":
            # Normal log entry
            payload = json.dumps(event["data"])
            yield sse_event(payload)

        elif event["type"] == "heartbeat":
            # Keep-alive comment (client ignores, just keeps TCP alive)
            yield ": ping\n\n"

        elif event["type"] == "error":
            # Error event (client can listen with addEventListener("error", ...))
            error_payload = json.dumps({
                "error": event.get("error"),
                "detail": event.get("detail"),
            })
            yield sse_event(error_payload, event="error")


class LogStreamView(APIView):
    """
    GET /api/logs/stream/

    Server-Sent Events endpoint for live log streaming.
    Returns a never-ending stream of ALL log entries from Elasticsearch.

    Authentication:
    - Happens once at connection start
    - Bearer token required in Authorization header
    - Token is NOT re-checked per-log (by design)

    Streams all logs from the last 30 seconds onwards, continuously.

    Example client (JavaScript):
        const token = 'your-jwt-token';
        const es = new EventSource('/api/logs/stream/', {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        es.addEventListener('message', (e) => {
            const log = JSON.parse(e.data);
            console.log(log);
        });

        es.addEventListener('error', (e) => {
            const error = JSON.parse(e.data);
            console.error(error.error, error.detail);
        });
    """
    authentication_classes = [CustomJWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Stream all live log entries as Server-Sent Events (SSE)",
        responses={200: "SSE stream of all log entries", 401: "Authentication required"},
        tags=["logs"],
    )
    def get(self, request):
        # ========== Step 1: Create Service & Generator ==========
        log_service = LogStreamService()
        generator = _sse_generator(log_service)

        # ========== Step 3: Return Streaming Response ==========
        return make_sse_response(generator)


class LogListView(APIView):
    """
    GET /api/logs/
    Paginated, filterable list of log entries from Elasticsearch.
    """
    authentication_classes = [CustomJWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    # --- drf_yasg swagger parameters (mirrors existing pattern in bulk_view.py) ---
    _params = [
        openapi.Parameter("level",       openapi.IN_QUERY, type=openapi.TYPE_STRING,
                          description="Filter by log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"),
        openapi.Parameter("component",   openapi.IN_QUERY, type=openapi.TYPE_STRING,
                          description="Filter by component (e.g. core, entities)"),
        openapi.Parameter("entity_type", openapi.IN_QUERY, type=openapi.TYPE_STRING,
                          description="Filter by entity_type (e.g. okta_user)"),
        openapi.Parameter("operation",   openapi.IN_QUERY, type=openapi.TYPE_STRING,
                          description="Filter by operation (e.g. bulk_fetch, restore)"),
        openapi.Parameter("from_date",   openapi.IN_QUERY, type=openapi.TYPE_STRING,
                          description="ISO 8601 start datetime (inclusive)"),
        openapi.Parameter("to_date",     openapi.IN_QUERY, type=openapi.TYPE_STRING,
                          description="ISO 8601 end datetime (inclusive)"),
        openapi.Parameter("search",      openapi.IN_QUERY, type=openapi.TYPE_STRING,
                          description="Full-text search across message and exc_info fields"),
        openapi.Parameter("page",        openapi.IN_QUERY, type=openapi.TYPE_INTEGER,
                          description="Page number (1-indexed, default 1)"),
        openapi.Parameter("page_size",   openapi.IN_QUERY, type=openapi.TYPE_INTEGER,
                          description="Results per page (default 50, max 500)"),
    ]

    @swagger_auto_schema(
        operation_description="Query paginated log entries from Elasticsearch",
        manual_parameters=_params,
        responses={200: "Paginated log list", 400: "Invalid query params", 503: "ES unavailable"},
        tags=["logs"],
    )
    def get(self, request):
        request_id = getattr(request, "request_id", "N/A")

        # Validate query params
        param_serializer = LogQueryParamsSerializer(data=request.query_params)
        if not param_serializer.is_valid():
            return Response(param_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        params = param_serializer.validated_data

        body = build_log_query(
            level=params.get("level"),
            component=params.get("component"),
            entity_type=params.get("entity_type"),
            operation=params.get("operation"),
            from_date=params.get("from_date"),
            to_date=params.get("to_date"),
            search=params.get("search"),
            page=params["page"],
            page_size=params["page_size"],
        )

        try:
            es = get_es_client()
            result = es.search(index=INDEX_PATTERN, body=body)
        except ESConnectionError as exc:
            logger.error(
                "Elasticsearch unavailable during log query",
                extra={"component": "logs", "request_id": request_id, "error": str(exc)},
            )
            return Response(
                {"error": "Log service unavailable. Elasticsearch cannot be reached."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except ESRequestError as exc:
            logger.error(
                "Elasticsearch request error during log query",
                extra={"component": "logs", "request_id": request_id, "error": str(exc)},
            )
            return Response(
                {"error": "Invalid query sent to Elasticsearch.", "detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            logger.exception(
                "Unexpected error querying Elasticsearch logs",
                extra={"component": "logs", "request_id": request_id},
            )
            return Response(
                {"error": "Internal server error querying logs."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        hits = result["hits"]["hits"]
        total = result["hits"]["total"]["value"]

        docs = [_hit_to_dict(h) for h in hits]
        serializer = LogEntrySerializer(docs, many=True)

        return Response({
            "count": total,
            "page": params["page"],
            "page_size": params["page_size"],
            "results": serializer.data,
        }, status=status.HTTP_200_OK)


class LogSummaryView(APIView):
    """
    GET /api/logs/summary/
    Returns aggregated counts for dashboard widgets.
    """
    authentication_classes = [CustomJWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get aggregated log summary for dashboard widgets (24h overview + 1h breakdowns)",
        responses={200: "Summary aggregations", 503: "ES unavailable"},
        tags=["logs"],
    )
    def get(self, request):
        request_id = getattr(request, "request_id", "N/A")
        body = build_summary_query()

        try:
            es = get_es_client()
            result = es.search(index=INDEX_PATTERN, body=body)
        except ESConnectionError as exc:
            logger.error(
                "Elasticsearch unavailable during summary query",
                extra={"component": "logs", "request_id": request_id, "error": str(exc)},
            )
            return Response(
                {"error": "Log service unavailable. Elasticsearch cannot be reached."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception as exc:
            logger.exception(
                "Unexpected error querying Elasticsearch summary",
                extra={"component": "logs", "request_id": request_id},
            )
            return Response(
                {"error": "Internal server error querying log summary."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        aggs = result.get("aggs", result.get("aggregations", {}))

        # Format by_level into a flat dict  {level_name: count}
        by_level = {
            bucket["key"]: bucket["doc_count"]
            for bucket in aggs.get("by_level", {}).get("buckets", [])
        }

        by_component = {
            bucket["key"]: bucket["doc_count"]
            for bucket in aggs.get("by_component", {}).get("buckets", [])
        }

        # Format by_level_last_1h (nested aggregation within filter agg)
        by_level_last_1h = {
            bucket["key"]: bucket["doc_count"]
            for bucket in aggs.get("by_level_last_1h", {}).get("levels", {}).get("buckets", [])
        }

        errors_last_1h = aggs.get("errors_last_1h", {}).get("doc_count", 0)
        total_last_1h = aggs.get("total_last_1h", {}).get("doc_count", 0)

        error_rate = round(errors_last_1h / total_last_1h * 100, 2) if total_last_1h > 0 else 0.0

        return Response({
            "total_last_1h": total_last_1h,
            "by_level_last_1h": by_level_last_1h,
            "by_level": by_level,
            "by_component": by_component,
            "errors_last_1h": errors_last_1h,
            "error_rate_last_1h_pct": error_rate,
        }, status=status.HTTP_200_OK)


class LogTraceView(APIView):
    """
    GET /api/logs/<request_id>/
    Returns all log entries for a specific request_id, sorted chronologically.
    """
    authentication_classes = [CustomJWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Retrieve all log entries for a specific request_id trace",
        responses={200: "Log trace entries", 404: "No logs for this request_id", 503: "ES unavailable"},
        tags=["logs"],
    )
    def get(self, request, request_id):
        calling_request_id = getattr(request, "request_id", "N/A")
        body = build_request_trace_query(request_id)

        try:
            es = get_es_client()
            result = es.search(index=INDEX_PATTERN, body=body)
        except ESConnectionError as exc:
            logger.error(
                "Elasticsearch unavailable during trace query",
                extra={"component": "logs", "request_id": calling_request_id, "error": str(exc)},
            )
            return Response(
                {"error": "Log service unavailable. Elasticsearch cannot be reached."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception as exc:
            logger.exception(
                "Unexpected error querying Elasticsearch trace",
                extra={"component": "logs", "request_id": calling_request_id},
            )
            return Response(
                {"error": "Internal server error querying log trace."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        hits = result["hits"]["hits"]
        total = result["hits"]["total"]["value"]

        if total == 0:
            return Response(
                {"error": f"No logs found for request_id: {request_id}"},
                status=status.HTTP_404_NOT_FOUND,
            )

        docs = [_hit_to_dict(h) for h in hits]
        serializer = LogEntrySerializer(docs, many=True)

        return Response({
            "request_id": request_id,
            "count": total,
            "entries": serializer.data,
        }, status=status.HTTP_200_OK)
