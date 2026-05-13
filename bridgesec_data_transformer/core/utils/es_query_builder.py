"""
Elasticsearch query DSL builders for log retrieval endpoints.
"""

INDEX_PATTERN = "bridgesec-logs-*"
DEFAULT_SORT_FIELD = "@timestamp"


def build_log_query(
    level=None,
    component=None,
    entity_type=None,
    operation=None,
    from_date=None,
    to_date=None,
    search=None,
    page=1,
    page_size=50,
) -> dict:
    """
    Build an Elasticsearch query dict for the paginated log list endpoint.
    Returns a dict ready to be passed as the `body` argument to es.search().
    """
    must_clauses = []
    filter_clauses = []

    # --- Keyword term filters (fields are mapped as pure keyword, no .keyword sub-field) ---
    if level:
        filter_clauses.append({"term": {"levelname": level}})
    if component:
        filter_clauses.append({"term": {"component": component}})
    if entity_type:
        filter_clauses.append({"term": {"entity_type": entity_type}})
    if operation:
        filter_clauses.append({"term": {"operation": operation}})

    # --- Date range filter ---
    range_clause = {}
    if from_date:
        range_clause["gte"] = from_date.isoformat()
    if to_date:
        range_clause["lte"] = to_date.isoformat()
    if range_clause:
        filter_clauses.append({"range": {"@timestamp": range_clause}})

    # --- Full-text search across message and exc_info ---
    if search:
        must_clauses.append({
            "multi_match": {
                "query": search,
                "fields": ["message", "exc_info"],
                "type": "best_fields",
                "fuzziness": "AUTO",
            }
        })

    # Assemble bool query
    bool_query = {}
    if must_clauses:
        bool_query["must"] = must_clauses
    if filter_clauses:
        bool_query["filter"] = filter_clauses

    query = {"bool": bool_query} if bool_query else {"match_all": {}}

    from_offset = (page - 1) * page_size

    return {
        "query": query,
        "sort": [{DEFAULT_SORT_FIELD: {"order": "desc"}}],
        "from": from_offset,
        "size": page_size,
    }


def build_summary_query() -> dict:
    """
    Build an ES aggregation query for the summary/dashboard endpoint.
    Returns counts by level, counts by component, and recent error rate.
    """
    return {
        "size": 0,
        "query": {
            "range": {
                "@timestamp": {
                    "gte": "now-24h",   # last 24 hours window for dashboard widgets
                    "lte": "now",
                }
            }
        },
        "aggs": {
            "by_level": {
                "terms": {
                    "field": "levelname",
                    "size": 10,
                }
            },
            "by_component": {
                "terms": {
                    "field": "component",
                    "size": 20,
                }
            },
            "by_level_last_1h": {
                "filter": {
                    "range": {"@timestamp": {"gte": "now-1h"}}
                },
                "aggs": {
                    "levels": {
                        "terms": {
                            "field": "levelname",
                            "size": 10,
                        }
                    }
                }
            },
            "errors_last_1h": {
                "filter": {
                    "bool": {
                        "must": [
                            {"terms": {"levelname": ["ERROR", "CRITICAL"]}},
                            {"range": {"@timestamp": {"gte": "now-1h"}}}
                        ]
                    }
                }
            },
            "total_last_1h": {
                "filter": {
                    "range": {"@timestamp": {"gte": "now-1h"}}
                }
            },
        },
    }


def build_request_trace_query(request_id: str) -> dict:
    """
    Build a query to retrieve all log entries for a single request_id.
    Sorted oldest-first to read as a trace timeline.
    """
    return {
        "query": {
            "term": {"request_id": request_id}
        },
        "sort": [{"@timestamp": {"order": "asc"}}],
        "size": 1000,  # A single request produces at most a few hundred log lines
    }


def build_live_log_query(
    last_timestamp: str,
    level=None,
    component=None,
    entity_type=None,
    operation=None,
    search=None,
    page_size: int = 100,
) -> dict:
    """
    Build an ES query for live streaming — returns logs newer than last_timestamp.

    Key difference from build_log_query:
    - Uses `gt` (strictly greater than) instead of `gte` on @timestamp
      → Prevents duplicate delivery on repeated polls
    - Sort order is `asc` (oldest-first)
      → Client sees logs in chronological order
    - No pagination `from` offset
      → Always returns next batch from cursor

    Args:
        last_timestamp: ISO-8601 string (e.g., "2026-04-07T10:00:00.000Z")
                       Cursor from previous poll
        level: Filter by log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        component: Filter by component (celery, okta_api, mongodb, etc.)
        entity_type: Filter by entity type (okta_user, okta_app, etc.)
        operation: Filter by operation (bulk_fetch, restore, etc.)
        search: Full-text search across message and exc_info fields
        page_size: Max logs to return per query (default: 100)

    Returns:
        ES DSL query dict ready for es.search(index=..., body=...)
    """
    # Always filter to logs AFTER the cursor timestamp
    filter_clauses = [{"range": {"@timestamp": {"gt": last_timestamp}}}]
    must_clauses = []

    # Keyword filters — fields are mapped as pure keyword type in this index
    if level:
        filter_clauses.append({"term": {"levelname": level}})
    if component:
        filter_clauses.append({"term": {"component": component}})
    if entity_type:
        filter_clauses.append({"term": {"entity_type": entity_type}})
    if operation:
        filter_clauses.append({"term": {"operation": operation}})

    # Full-text search on message and exception info
    if search:
        must_clauses.append({
            "multi_match": {
                "query": search,
                "fields": ["message", "exc_info"],
                "type": "best_fields",
                "fuzziness": "AUTO",
            }
        })

    # Build bool query
    bool_query = {"filter": filter_clauses}
    if must_clauses:
        bool_query["must"] = must_clauses

    return {
        "query": {"bool": bool_query},
        "sort": [{DEFAULT_SORT_FIELD: {"order": "asc"}}],  # Oldest first
        "size": page_size,
    }
