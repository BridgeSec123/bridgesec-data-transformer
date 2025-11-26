from urllib.parse import quote

from django.conf import settings
from django.shortcuts import redirect
from rest_framework.views import APIView


class OktaLoginView(APIView):
    def get(self, request):
        # URL encode the scopes to handle special characters
        encoded_scopes = quote(settings.OKTA_SCOPES, safe='')

        authorize_url = (
            f"{settings.OKTA_ISSUER}/oauth2/v1/authorize?"
            f"client_id={settings.OKTA_CLIENT_ID}&"
            f"response_type=code&"
            f"scope={encoded_scopes}&"
            f"redirect_uri={settings.OKTA_REDIRECT_URI}&"
            f"state=xyz&nonce=abc&"
            f"prompt=login"
        )
        return redirect(authorize_url)


