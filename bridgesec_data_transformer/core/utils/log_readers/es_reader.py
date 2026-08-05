"""
Elasticsearch implementation of LogReader — wraps the existing
es_query_builder.py query DSL and es_client.py client (unchanged behavior,
just moved behind the shared LogReader interface).
"""
from core.utils.es_client import get_es_client
from core.utils.es_query_builder import (
    INDEX_PATTERN,
    build_log_query,
    build_summary_query,
    build_request_trace_query,
    build_live_log_query,
)
from core.utils.log_readers.base import LogReader


def _hit_to_dict(hit: dict) -> dict:
    doc = hit.get("_source", {})
    doc["_id"] = hit.get("_id")
    if "@timestamp" in doc and "timestamp" not in doc:
        doc["timestamp"] = doc["@timestamp"]
    return doc


class ElasticsearchLogReader(LogReader):
    def __init__(self):
        self._es = get_es_client()

    def search(self, tenant_id, level=None, component=None, entity_type=None,
               operation=None, from_date=None, to_date=None, search=None,
               page=1, page_size=50):
        body = build_log_query(
            level=level, component=component, entity_type=entity_type,
            operation=operation, from_date=from_date, to_date=to_date,
            search=search, page=page, page_size=page_size, tenant_id=tenant_id,
        )
        result = self._es.search(index=INDEX_PATTERN, body=body)
        hits = result["hits"]["hits"]
        total = result["hits"]["total"]["value"]
        return [_hit_to_dict(h) for h in hits], total

    def summary(self, tenant_id):
        body = build_summary_query(tenant_id=tenant_id)
        result = self._es.search(index=INDEX_PATTERN, body=body)
        aggs = result.get("aggs", result.get("aggregations", {}))

        by_level = {b["key"]: b["doc_count"] for b in aggs.get("by_level", {}).get("buckets", [])}
        by_component = {b["key"]: b["doc_count"] for b in aggs.get("by_component", {}).get("buckets", [])}
        by_level_last_1h = {
            b["key"]: b["doc_count"]
            for b in aggs.get("by_level_last_1h", {}).get("levels", {}).get("buckets", [])
        }
        errors_last_1h = aggs.get("errors_last_1h", {}).get("doc_count", 0)
        total_last_1h = aggs.get("total_last_1h", {}).get("doc_count", 0)
        error_rate = round(errors_last_1h / total_last_1h * 100, 2) if total_last_1h > 0 else 0.0

        return {
            "total_last_1h": total_last_1h,
            "by_level_last_1h": by_level_last_1h,
            "by_level": by_level,
            "by_component": by_component,
            "errors_last_1h": errors_last_1h,
            "error_rate_last_1h_pct": error_rate,
        }

    def trace(self, tenant_id, request_id):
        body = build_request_trace_query(request_id, tenant_id=tenant_id)
        result = self._es.search(index=INDEX_PATTERN, body=body)
        return [_hit_to_dict(h) for h in result["hits"]["hits"]]

    def tail(self, tenant_id, last_timestamp, level=None, component=None,
             entity_type=None, operation=None, search=None, page_size=100):
        body = build_live_log_query(
            last_timestamp=last_timestamp, level=level, component=component,
            entity_type=entity_type, operation=operation, search=search,
            page_size=page_size, tenant_id=tenant_id,
        )
        result = self._es.search(index=INDEX_PATTERN, body=body)
        return [_hit_to_dict(h) for h in result["hits"]["hits"]]
