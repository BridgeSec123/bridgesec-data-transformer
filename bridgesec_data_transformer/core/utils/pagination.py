import requests
from core.utils.rate_limit import handle_rate_limit

def fetch_all_pages(initial_url, headers):
    """Fetches all paginated data from Okta API if pagination exists."""
    all_data = []
    okta_url = initial_url

    while okta_url:
        response = requests.get(okta_url, headers=headers)

        if handle_rate_limit(response):  # Wait and retry if rate limit is exceeded
            continue

        if response.status_code != 200:
            return {"error": f"Failed to fetch data from Okta API: {response.text}"}, response.status_code

        response_data = response.json()
        all_data.extend(response_data)

        # Check if pagination exists
        okta_url = response.links.get("next", {}).get("url")

    return all_data