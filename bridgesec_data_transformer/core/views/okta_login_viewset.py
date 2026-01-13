from urllib.parse import quote

from django.conf import settings
from django.shortcuts import redirect
from rest_framework.views import APIView


class OktaLoginView(APIView):
    def get(self, request):
        # URL encode the scopes to handle special characters
        encoded_scopes = quote(settings.OKTA_SCOPES, safe='')

        # Normalize OKTA_ISSUER - remove trailing slash if present
        issuer_base = settings.OKTA_ISSUER.rstrip('/')

        # Build authorize URL - handle both org and custom auth servers
        # If issuer already contains /oauth2/{authServerId}, use /v1/authorize
        # Otherwise, use /oauth2/v1/authorize (org auth server)
        if '/oauth2/' in issuer_base:
            # Custom authorization server (e.g., /oauth2/default)
            authorize_url = (
                f"{issuer_base}/v1/authorize?"
                f"client_id={settings.OKTA_CLIENT_ID}&"
                f"response_type=code&"
                f"scope={encoded_scopes}&"
                f"redirect_uri={settings.OKTA_REDIRECT_URI}&"
                f"state=xyz&nonce=abc&"
                f"prompt=login"
            )
        else:
            # Org authorization server
            authorize_url = (
                f"{issuer_base}/oauth2/v1/authorize?"
                f"client_id={settings.OKTA_CLIENT_ID}&"
                f"response_type=code&"
                f"scope={encoded_scopes}&"
                f"redirect_uri={settings.OKTA_REDIRECT_URI}&"
                f"state=xyz&nonce=abc&"
                f"prompt=login"
            )

        return redirect(authorize_url)


