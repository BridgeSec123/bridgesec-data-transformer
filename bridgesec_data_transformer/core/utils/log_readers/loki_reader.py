"""
Loki implementation of LogReader — runs LogQL queries via Loki's
/loki/api/v1/query_range against the {app="bridgesec"} stream written by
LokiHandler (see log_router.py), whose lines are JSON docs from
ElasticsearchHandler._record_to_doc().
"""
import json
import logging

import requests

from core.utils.log_readers.base import LogReader

logger = logging.getLogger(__name__)

_NANOS_PER_SECOND = 1_000_000_000


def _logql_selector(tenant_id=None):
    labels = ['app="bridgesec"']
    if tenant_id:
        labels.append(f'tenant_id="{tenant_id}"')
    return "{" + ", ".join(labels) + "}"


def _logql_filters(level=None, component=None, entity_type=None, operation=None, search=None):
    pipeline = "| json"
    if level:
        pipeline += f' | levelname="{level}"'
    if component:
        pipeline += f' | component="{component}"'
    if entity_type:
        pipeline += f' | entity_type="{entity_type}"'
    if operation:
        pipeline += f' | operation="{operation}"'
    if search:
        pipeline += f' |~ "(?i){search}"'
    return pipeline


class LokiLogReader(LogReader):
    def __init__(self, config: dict):
        self._query_url = config["query_url"].rstrip("/")
        self._verify = config.get("verify_ssl", True)

    def _query_range(self, logql, start_ns, end_ns, limit=100, direction="backward"):
        resp = requests.get(
            f"{self._query_url}/loki/api/v1/query_range",
            params={
                "query": logql, "start": start_ns, "end": end_ns,
                "limit": limit, "direction": direction,
            },
            timeout=15,
            verify=self._verify,
        )
        resp.raise_for_status()
        streams = resp.json().get("data", {}).get("result", [])
        docs = []
        for stream in streams:
            for ts_ns, line in stream.get("values", []):
                try:
                    doc = json.loads(line)
                except (ValueError, TypeError):
                    doc = {"message": line}
                doc.setdefault("timestamp", None)
                doc["@timestamp"] = doc.get("timestamp") or doc.get("@timestamp")
                docs.append(doc)
        return docs

    def search(self, tenant_id, level=None, component=None, entity_type=None,
               operation=None, from_date=None, to_date=None, search=None,
               page=1, page_size=50):
        import time
        logql = f"{_logql_selector(tenant_id)} {_logql_filters(level, component, entity_type, operation, search)}"
        end_ns = int(time.time() * _NANOS_PER_SECOND)
        start_ns = end_ns - 30 * 24 * 3600 * _NANOS_PER_SECOND  # 30d lookback default
        docs = self._query_range(logql, start_ns, end_ns, limit=page * page_size)
        start = (page - 1) * page_size
        return docs[start:start + page_size], len(docs)

    def summary(self, tenant_id):
        import time
        selector = _logql_selector(tenant_id)
        end_ns = int(time.time() * _NANOS_PER_SECOND)

        docs_24h = self._query_range(f"{selector} | json", end_ns - 24 * 3600 * _NANOS_PER_SECOND, end_ns, limit=5000)
        docs_1h = self._query_range(f"{selector} | json", end_ns - 3600 * _NANOS_PER_SECOND, end_ns, limit=5000)

        by_level, by_component = {}, {}
        for d in docs_24h:
            lvl = d.get("levelname")
            comp = d.get("component")
            if lvl:
                by_level[lvl] = by_level.get(lvl, 0) + 1
            if comp:
                by_component[comp] = by_component.get(comp, 0) + 1

        by_level_last_1h = {}
        for d in docs_1h:
            lvl = d.get("levelname")
            if lvl:
                by_level_last_1h[lvl] = by_level_last_1h.get(lvl, 0) + 1

        total_last_1h = len(docs_1h)
        errors_last_1h = by_level_last_1h.get("ERROR", 0) + by_level_last_1h.get("CRITICAL", 0)
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
        import time
        logql = f'{_logql_selector(tenant_id)} | json | request_id="{request_id}"'
        end_ns = int(time.time() * _NANOS_PER_SECOND)
        start_ns = end_ns - 90 * 24 * 3600 * _NANOS_PER_SECOND
        docs = self._query_range(logql, start_ns, end_ns, limit=1000, direction="forward")
        return docs

    def tail(self, tenant_id, last_timestamp, level=None, component=None,
             entity_type=None, operation=None, search=None, page_size=100):
        import datetime
        import time
        logql = f"{_logql_selector(tenant_id)} {_logql_filters(level, component, entity_type, operation, search)}"
        start_dt = datetime.datetime.fromisoformat(last_timestamp.replace("Z", "+00:00"))
        start_ns = int(start_dt.timestamp() * _NANOS_PER_SECOND) + 1  # exclusive of last_timestamp
        end_ns = int(time.time() * _NANOS_PER_SECOND)
        return self._query_range(logql, start_ns, end_ns, limit=page_size, direction="forward")
