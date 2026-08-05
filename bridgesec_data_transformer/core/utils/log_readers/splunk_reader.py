"""
Splunk implementation of LogReader — runs SPL searches via Splunk's REST
search-jobs API (blocking exec_mode, no manual poll loop needed) against the
`bridgesec_logs` index written by SplunkHandler (sourcetype=_json).
"""
import logging

import requests

from core.utils.log_readers.base import LogReader

logger = logging.getLogger(__name__)


def _spl_escape(value: str) -> str:
    return str(value).replace('"', '\\"')


class SplunkLogReader(LogReader):
    def __init__(self, config: dict):
        self._search_url = config["search_url"].rstrip("/")
        self._auth = (config.get("search_user"), config.get("search_password"))
        # Self-signed certs are common for local/on-prem Splunk — tenant config
        # can opt out per-instance, but default to verifying like any other call.
        self._verify = config.get("verify_ssl", True)

    def _run(self, spl: str, earliest="-24h", latest="now", max_count=None):
        resp = requests.post(
            f"{self._search_url}/services/search/jobs",
            auth=self._auth,
            data={
                "search": spl,
                "exec_mode": "blocking",
                "output_mode": "json",
                "earliest_time": earliest,
                "latest_time": latest,
                **({"max_count": max_count} if max_count else {}),
            },
            timeout=30,
            verify=self._verify,
        )
        resp.raise_for_status()
        sid = resp.json()["sid"]

        results = requests.get(
            f"{self._search_url}/services/search/jobs/{sid}/results",
            auth=self._auth,
            params={"output_mode": "json", "count": max_count or 0},
            timeout=30,
            verify=self._verify,
        )
        results.raise_for_status()
        return results.json().get("results", [])

    @staticmethod
    def _filters_to_spl(tenant_id=None, level=None, component=None,
                         entity_type=None, operation=None, search=None):
        clauses = ['index=bridgesec_logs']
        if tenant_id:
            clauses.append(f'tenant_id="{_spl_escape(tenant_id)}"')
        if level:
            clauses.append(f'levelname="{_spl_escape(level)}"')
        if component:
            clauses.append(f'component="{_spl_escape(component)}"')
        if entity_type:
            clauses.append(f'entity_type="{_spl_escape(entity_type)}"')
        if operation:
            clauses.append(f'operation="{_spl_escape(operation)}"')
        if search:
            clauses.append(f'"{_spl_escape(search)}"')
        return " ".join(clauses)

    def search(self, tenant_id, level=None, component=None, entity_type=None,
               operation=None, from_date=None, to_date=None, search=None,
               page=1, page_size=50):
        spl = self._filters_to_spl(tenant_id, level, component, entity_type, operation, search)
        spl = f"search {spl} | sort -_time | head {page * page_size}"
        rows = self._run(spl, earliest=from_date or "-30d", latest=to_date or "now")
        start = (page - 1) * page_size
        return rows[start:start + page_size], len(rows)

    def summary(self, tenant_id):
        base = f'index=bridgesec_logs tenant_id="{_spl_escape(tenant_id)}"' if tenant_id else "index=bridgesec_logs"

        by_level_rows = self._run(f"search {base} earliest=-24h | stats count by levelname")
        by_component_rows = self._run(f"search {base} earliest=-24h | stats count by component")
        by_level_1h_rows = self._run(f"search {base} earliest=-1h | stats count by levelname")
        total_1h_rows = self._run(f"search {base} earliest=-1h | stats count")

        by_level = {r["levelname"]: int(r["count"]) for r in by_level_rows if r.get("levelname")}
        by_component = {r["component"]: int(r["count"]) for r in by_component_rows if r.get("component")}
        by_level_last_1h = {r["levelname"]: int(r["count"]) for r in by_level_1h_rows if r.get("levelname")}
        total_last_1h = int(total_1h_rows[0]["count"]) if total_1h_rows else 0
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
        spl = f'search index=bridgesec_logs request_id="{_spl_escape(request_id)}"'
        if tenant_id:
            spl += f' tenant_id="{_spl_escape(tenant_id)}"'
        spl += " | sort _time"
        return self._run(spl, earliest="-90d", latest="now", max_count=1000)

    def tail(self, tenant_id, last_timestamp, level=None, component=None,
             entity_type=None, operation=None, search=None, page_size=100):
        spl = self._filters_to_spl(tenant_id, level, component, entity_type, operation, search)
        spl = f"search {spl} | sort _time | head {page_size}"
        return self._run(spl, earliest=last_timestamp, latest="now", max_count=page_size)
