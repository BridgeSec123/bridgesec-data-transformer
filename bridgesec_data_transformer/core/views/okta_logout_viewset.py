import logging
from rest_framework.views import APIView
from django.http import HttpResponseRedirect
from django.conf import settings

logger = logging.getLogger(__name__)

class OktaLogoutView(APIView):
    def get(self, request):
        user_email = request.session.get("email")
        logger.info(f"Logging out user: {user_email}")

        # Clear the session
        request.session.flush()
        logger.info("Session flushed successfully.")

        # Build frontend redirect URL
        redirect_url = f"{settings.FRONTEND_URL}/sign-in"
        

        # Prepare response and delete cookie
        response = HttpResponseRedirect(redirect_url)
        response.delete_cookie("access_token")
        logger.info("access_token cookie deleted. Redirecting...")

        return response
