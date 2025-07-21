from django.conf import settings
from django.shortcuts import redirect
from rest_framework.views import APIView

class OktaLoginView(APIView):
    def get(self, request):
        authorize_url = (
            f"{settings.OKTA_ISSUER}/v1/authorize?"
            f"client_id={settings.OKTA_CLIENT_ID}&"
            f"response_type=code&scope=openid email profile&"
            f"redirect_uri={settings.OKTA_REDIRECT_URI}&"
            f"state=xyz&nonce=abc&"
            f"prompt=login"
        )
        return redirect(authorize_url)


