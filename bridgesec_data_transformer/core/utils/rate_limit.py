import time
def rate_limit_headers(okta_response):
    """
    Attach rate limit headers from Okta's response to Django's response.
    """
    return {
        "X-Rate-Limit-Limit": okta_response.headers.get("X-Rate-Limit-Limit", "unknown"),
        "X-Rate-Limit-Remaining": okta_response.headers.get("X-Rate-Limit-Remaining", "unknown"),
        "X-Rate-Limit-Reset": okta_response.headers.get("X-Rate-Limit-Reset", "unknown"),
    }
    
def handle_rate_limit(response):
    """Handles API rate limiting by waiting until the reset time."""
    if response.status_code == 429:  # Too many requests
        reset_time = int(response.headers.get("X-Rate-Limit-Reset", time.time()))
        wait_time = max(reset_time - time.time(), 1)
        print(f"Rate limit exceeded. Waiting for {wait_time} seconds...")
        time.sleep(wait_time)
        return True  # Indicate that we need to retry

    return False 