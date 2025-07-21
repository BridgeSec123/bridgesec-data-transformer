import logging
from rest_framework.views import APIView
from django.http import HttpResponseRedirect
from django.conf import settings

logger = logging.getLogger(__name__)

class OktaLogoutView(APIView):
    def get(self, request):
        user_email = request.session.get("email")
        id_token = request.session.get("id_token")
        
        logger.info(f"Logging out user: {user_email}")

        # Build redirect fallback
        redirect_url = f"{settings.FRONTEND_URL}/sign-in"

        # If no id_token found (already expired), just do soft logout
        if not id_token:
            logger.warning("No id_token in session; performing soft logout.")
            request.session.flush()
            response = HttpResponseRedirect(redirect_url)
            response.delete_cookie("access_token")
            return response

        # Okta logout URL
        logout_url = (
            f"{settings.OKTA_ISSUER}/v1/logout?"
            f"id_token_hint={id_token}&"
            f"post_logout_redirect_uri={redirect_url}"
        )

        # Clear local session + cookie
        request.session.flush()
        response = HttpResponseRedirect(logout_url)
        response.delete_cookie("access_token")
        return response
