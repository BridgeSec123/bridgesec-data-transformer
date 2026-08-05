"""
Shared contract every log reader (ES/Splunk/Loki) implements.

All four methods return docs in the shape LogEntrySerializer expects:
levelname, message, tenant_id, user_email, @timestamp/timestamp, request_id,
component, entity_type, operation, action.
"""


class LogReader:
    def search(self, tenant_id, level=None, component=None, entity_type=None,
               operation=None, from_date=None, to_date=None, search=None,
               page=1, page_size=50):
        """Return (docs: list[dict], total: int)."""
        raise NotImplementedError

    def summary(self, tenant_id):
        """Return {total_last_1h, by_level_last_1h, by_level, by_component,
        errors_last_1h, error_rate_last_1h_pct}."""
        raise NotImplementedError

    def trace(self, tenant_id, request_id):
        """Return docs: list[dict] for one request_id, chronological."""
        raise NotImplementedError

    def tail(self, tenant_id, last_timestamp, level=None, component=None,
             entity_type=None, operation=None, search=None, page_size=100):
        """Return docs: list[dict] newer than last_timestamp, oldest first."""
        raise NotImplementedError
