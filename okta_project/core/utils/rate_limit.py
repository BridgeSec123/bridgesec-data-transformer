def rate_limit_headers(okta_response):
    """
    Attach rate limit headers from Okta's response to Django's response.
    """
    return {
        "X-Rate-Limit-Limit": okta_response.headers.get("X-Rate-Limit-Limit", "unknown"),
        "X-Rate-Limit-Remaining": okta_response.headers.get("X-Rate-Limit-Remaining", "unknown"),
        "X-Rate-Limit-Reset": okta_response.headers.get("X-Rate-Limit-Reset", "unknown"),
    }