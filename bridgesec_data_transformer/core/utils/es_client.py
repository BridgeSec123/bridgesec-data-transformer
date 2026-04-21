import os
import logging
from elasticsearch import Elasticsearch, ConnectionError, NotFoundError, RequestError

logger = logging.getLogger(__name__)

_es_client = None


def get_es_client() -> Elasticsearch:
    """
    Return a module-level Elasticsearch client singleton.
    Reads ELASTICSEARCH_URL from the environment, defaulting to http://localhost:9200.
    """
    global _es_client
    if _es_client is None:
        url = os.environ.get("ELASTICSEARCH_URL", "http://localhost:9200")
        _es_client = Elasticsearch(
            url,
            retry_on_timeout=True,
            max_retries=2,
            request_timeout=10,
        )
        logger.info(f"Elasticsearch client initialized: {url}")
    return _es_client


# Re-export ES exception types so callers don't need to import elasticsearch directly
__all__ = ["get_es_client", "ConnectionError", "NotFoundError", "RequestError"]
