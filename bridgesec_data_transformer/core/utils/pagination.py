import logging

import requests
from core.utils.rate_limit import handle_rate_limit

logger = logging.getLogger(__name__)

def fetch_all_pages(initial_url, headers, request=None):
    """
    Fetches all paginated data from Okta API if pagination exists.

    request: optional — when the session's token is DPoP-bound, each page has a
    different URL and DPoP proofs are single-use and URL-bound, so `headers` (built
    for the first page) must be regenerated per page rather than reused. Pass the
    request through so that can happen; omit it for plain-Bearer sessions, where
    the same `headers` dict is valid for every page.
    """
    logger.info("Fetching all paginated data from Okta API")
    all_data = []
    okta_url = initial_url

    while okta_url:
        if request is not None:
            from core.utils.okta_helpers import get_okta_headers
            headers = get_okta_headers(request, method="GET", url=okta_url)
        response = requests.get(okta_url, headers=headers)

        if handle_rate_limit(response):  # Wait and retry if rate limit is exceeded
            logger.warning("Rate limit reached while fetching paginated data. Retrying...")
            continue

        if response.status_code != 200:
            logger.error(f"Failed to fetch paginated data from Okta API: {response.text}")
            return {"error": f"Failed to fetch data from Okta API: {response.text}"}, response.status_code

        response_data = response.json()
        all_data.extend(response_data)
        logger.info(f"Fetched {len(response_data)} records from paginated response")
        
        # Check if pagination exists
        okta_url = response.links.get("next", {}).get("url")
    logger.info(f"Total records fetched from all pages: {len(all_data)}")
    return all_data