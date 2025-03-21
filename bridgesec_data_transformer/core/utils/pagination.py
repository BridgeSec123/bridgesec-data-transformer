import logging

import requests
from core.utils.rate_limit import handle_rate_limit

logger = logging.getLogger(__name__)

def fetch_all_pages(initial_url, headers):
    """Fetches all paginated data from Okta API if pagination exists."""
    logger.info("Fetching all paginated data from Okta API")
    all_data = []
    okta_url = initial_url

    while okta_url:
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