"""
Logs API endpoints - query Elasticsearch for application logs.
"""
import logging
from datetime import datetime, timedelta
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from core.authentication import CustomJWTAuthentication
from core.utils.es_client import get_es_client, ConnectionError, NotFoundError

logger = logging.getLogger(__name__)

INDEX_PATTERN = "bridgesec-logs-*"
MAX_PAGE_SIZE = 500


class LogsListView(APIView):
    """
    Query logs with flexible filtering and pagination.
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter("level", openapi.IN_QUERY, type=openapi.TYPE_STRING, description="DEBUG, INFO, WARNING, ERROR, CRITICAL"),
            openapi.Parameter("component", openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Filter by component"),
            openapi.Parameter("entity_type", openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Filter by entity type"),
            openapi.Parameter("operation", openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Filter by operation"),
            openapi.Parameter("from_date", openapi.IN_QUERY, type=openapi.TYPE_STRING, description="ISO-8601 start date"),
            openapi.Parameter("to_date", openapi.IN_QUERY, type=openapi.TYPE_STRING, description="ISO-8601 end date"),
            openapi.Parameter("search", openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Full-text search in message/exc_info"),
            openapi.Parameter("page", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="Page number (1-indexed)", default=1),
            openapi.Parameter("page_size", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="Results per page (max 500)", default=50),
        ],
        responses={
            200: openapi.Response(
                description="Paginated log list",
                examples={
                    "application/json": {
                        "count": 1542,
                        "page": 1,
                        "page_size": 50,
                        "results": [
                            {
                                "id": "abc123",
                                "timestamp": "2026-04-03T14:35:22.123456Z",
                                "levelname": "ERROR",
                                "message": "Failed to fetch okta_user",
                                "component": "entities",
                                "entity_type": "okta_user",
                                "request_id": "550e8400-e29b-41d4-a716-446655440000",
                                "user": "john.doe@adjecti.com",
                                "operation": "bulk_fetch",
                                "duration_ms": 3245.67,
                                "resource_count": 0,
                                "hostname": "bridgesec-api-pod-1",
                                "environment": "production",
                                "exc_info": None
                            }
                        ]
                    }
                }
            ),
            400: openapi.Response(description="Bad request"),
            503: openapi.Response(description="Elasticsearch unavailable"),
        }
    )
    def get(self, request, *args, **kwargs):
        """Get paginated logs with optional filters."""
        try:
            # Parse query parameters
            level = request.query_params.get("level", "").upper() or None
            component = request.query_params.get("component", "").strip() or None
            entity_type = request.query_params.get("entity_type", "").strip() or None
            operation = request.query_params.get("operation", "").strip() or None
            from_date = request.query_params.get("from_date", "").strip() or None
            to_date = request.query_params.get("to_date", "").strip() or None
            search = request.query_params.get("search", "").strip() or None

            try:
                page = int(request.query_params.get("page", 1))
                page_size = min(int(request.query_params.get("page_size", 50)), MAX_PAGE_SIZE)
                if page < 1:
                    page = 1
                if page_size < 1:
                    page_size = 50
            except ValueError:
                return Response(
                    {"error": "Invalid page or page_size - must be integers"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Build Elasticsearch query
            query_filters = []

            if level:
                query_filters.append({"term": {"levelname": level}})
            if component:
                query_filters.append({"term": {"component": component}})
            if entity_type:
                query_filters.append({"term": {"entity_type": entity_type}})
            if operation:
                query_filters.append({"term": {"operation": operation}})

            # Date range
            if from_date or to_date:
                range_filter = {}
                if from_date:
                    try:
                        range_filter["gte"] = from_date
                    except Exception:
                        return Response(
                            {"error": "Invalid from_date format. Use ISO-8601"},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                if to_date:
                    try:
                        range_filter["lte"] = to_date
                    except Exception:
                        return Response(
                            {"error": "Invalid to_date format. Use ISO-8601"},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                if range_filter:
                    query_filters.append({"range": {"timestamp": range_filter}})

            # Build query
            es_query = {
                "from": (page - 1) * page_size,
                "size": page_size,
                "sort": [{"timestamp": {"order": "desc"}}],
            }

            if query_filters or search:
                bool_query = {}

                if search:
                    bool_query["must"] = [
                        {
                            "multi_match": {
                                "query": search,
                                "fields": ["message", "exc_info"],
                                "fuzziness": "AUTO"
                            }
                        }
                    ]

                if query_filters:
                    bool_query["filter"] = query_filters

                es_query["query"] = {"bool": bool_query}
            else:
                es_query["query"] = {"match_all": {}}

            logger.debug(f"Executing ES query: {es_query}")

            # Execute query
            es = get_es_client()
            response = es.search(index=INDEX_PATTERN, body=es_query)

            # Parse response
            total_hits = response["hits"]["total"]["value"]
            hits = response["hits"]["hits"]

            results = []
            for hit in hits:
                doc = hit["_source"]
                results.append({
                    "id": hit["_id"],
                    **doc
                })

            return Response({
                "count": total_hits,
                "page": page,
                "page_size": page_size,
                "results": results
            }, status=status.HTTP_200_OK)

        except ConnectionError:
            logger.error("Elasticsearch connection failed")
            return Response(
                {"error": "Log service unavailable. Elasticsearch cannot be reached."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as e:
            logger.exception("Error querying logs")
            return Response(
                {"error": f"Failed to query logs: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LogsSummaryView(APIView):
    """
    Get aggregated log statistics for the past 24 hours.
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses={
            200: openapi.Response(
                description="Log statistics for past 24 hours",
                examples={
                    "application/json": {
                        "by_level": {
                            "DEBUG": 2145,
                            "INFO": 8234,
                            "WARNING": 156,
                            "ERROR": 43,
                            "CRITICAL": 2
                        },
                        "by_component": {
                            "core": 3421,
                            "entities": 5123,
                            "terraform_workflow": 2036
                        },
                        "errors_last_1h": 8,
                        "total_last_1h": 892,
                        "error_rate_last_1h_pct": 0.9
                    }
                }
            ),
            503: openapi.Response(description="Elasticsearch unavailable"),
        }
    )
    def get(self, request, *args, **kwargs):
        """Get aggregated stats for past 24 hours."""
        try:
            es = get_es_client()

            # Aggregations for past 24 hours
            es_query = {
                "size": 0,
                "query": {
                    "range": {
                        "timestamp": {
                            "gte": "now-24h"
                        }
                    }
                },
                "aggs": {
                    "by_level": {
                        "terms": {
                            "field": "levelname",
                            "size": 10
                        }
                    },
                    "by_component": {
                        "terms": {
                            "field": "component",
                            "size": 50
                        }
                    }
                }
            }

            response = es.search(index=INDEX_PATTERN, body=es_query)

            # Parse aggregations
            by_level = {}
            for bucket in response["aggregations"]["by_level"]["buckets"]:
                by_level[bucket["key"]] = bucket["doc_count"]

            by_component = {}
            for bucket in response["aggregations"]["by_component"]["buckets"]:
                by_component[bucket["key"]] = bucket["doc_count"]

            # Errors and totals for past 1 hour
            es_query_1h = {
                "size": 0,
                "query": {
                    "bool": {
                        "must": [
                            {
                                "range": {
                                    "timestamp": {
                                        "gte": "now-1h"
                                    }
                                }
                            }
                        ]
                    }
                },
                "aggs": {
                    "errors": {
                        "filter": {
                            "terms": {
                                "levelname": ["ERROR", "CRITICAL"]
                            }
                        }
                    }
                }
            }

            response_1h = es.search(index=INDEX_PATTERN, body=es_query_1h)
            total_last_1h = response_1h["hits"]["total"]["value"]
            errors_last_1h = response_1h["aggregations"]["errors"]["doc_count"]
            error_rate = (errors_last_1h / total_last_1h * 100) if total_last_1h > 0 else 0.0

            return Response({
                "by_level": by_level,
                "by_component": by_component,
                "errors_last_1h": errors_last_1h,
                "total_last_1h": total_last_1h,
                "error_rate_last_1h_pct": round(error_rate, 2)
            }, status=status.HTTP_200_OK)

        except ConnectionError:
            logger.error("Elasticsearch connection failed")
            return Response(
                {"error": "Log service unavailable. Elasticsearch cannot be reached."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as e:
            logger.exception("Error fetching log summary")
            return Response(
                {"error": f"Failed to fetch summary: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LogsTraceView(APIView):
    """
    Get complete log trace for a single request ID.
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses={
            200: openapi.Response(
                description="Log trace for request",
                examples={
                    "application/json": {
                        "request_id": "550e8400-e29b-41d4-a716-446655440000",
                        "count": 7,
                        "entries": []
                    }
                }
            ),
            404: openapi.Response(description="No logs found for this request_id"),
            503: openapi.Response(description="Elasticsearch unavailable"),
        }
    )
    def get(self, request, request_id, *args, **kwargs):
        """Get all logs for a specific request ID."""
        try:
            es = get_es_client()

            # Query for all logs with this request_id
            es_query = {
                "size": 1000,
                "sort": [{"timestamp": {"order": "asc"}}],
                "query": {
                    "term": {
                        "request_id": request_id
                    }
                }
            }

            response = es.search(index=INDEX_PATTERN, body=es_query)
            hits = response["hits"]["hits"]

            if not hits:
                return Response(
                    {"error": f"No logs found for request_id: {request_id}"},
                    status=status.HTTP_404_NOT_FOUND
                )

            entries = []
            for hit in hits:
                doc = hit["_source"]
                entries.append({
                    "id": hit["_id"],
                    **doc
                })

            return Response({
                "request_id": request_id,
                "count": len(entries),
                "entries": entries
            }, status=status.HTTP_200_OK)

        except ConnectionError:
            logger.error("Elasticsearch connection failed")
            return Response(
                {"error": "Log service unavailable. Elasticsearch cannot be reached."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as e:
            logger.exception(f"Error fetching trace for request_id {request_id}")
            return Response(
                {"error": f"Failed to fetch trace: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
