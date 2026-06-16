import logging
from rest_framework.views import APIView
from django.http import HttpResponseRedirect
from django.conf import settings

logger = logging.getLogger(__name__)

class OktaLogoutView(APIView):
    def get(self, request):
        request_id = getattr(request, 'request_id', 'N/A')
        user_email = request.session.get("email")
        id_token = request.session.get("id_token")

        logger.info(
            f"User logout initiated: {user_email}",
            extra={
                'component': 'auth',
                'request_id': request_id,
                'user': user_email,
                'action': 'logout',
            }
        )

        # Build redirect fallback
        redirect_url = f"{settings.FRONTEND_URL}/sign-in"

        # If no id_token found (already expired), just do soft logout
        if not id_token:
            logger.warning(
                f"No id_token in session for {user_email}; performing soft logout",
                extra={
                    'component': 'auth',
                    'request_id': request_id,
                    'user': user_email,
                    'action': 'soft_logout',
                }
            )
            request.session.flush()
            response = HttpResponseRedirect(redirect_url)
            response.delete_cookie("access_token")
            return response

        # Resolve tenant-specific issuer from session tenant_id → Supabase
        okta_issuer = settings.OKTA_ISSUER.rstrip('/')
        tenant_id = request.session.get("tenant_id")
        if tenant_id and getattr(settings, 'MULTI_TENANCY_ENABLED', False):
            from core.utils.tenant_utils import get_tenant_by_id
            tenant = get_tenant_by_id(tenant_id)
            if tenant and tenant.okta_issuer:
                okta_issuer = tenant.okta_issuer.rstrip('/')

        # Okta logout URL
        logout_url = (
            f"{okta_issuer}/v1/logout?"
            f"id_token_hint={id_token}&"
            f"post_logout_redirect_uri={redirect_url}"
        )

        # Clear local session + cookie
        request.session.flush()

        logger.info(
            f"User logged out successfully: {user_email}",
            extra={
                'component': 'auth',
                'request_id': request_id,
                'user': user_email,
                'action': 'logout_complete',
            }
        )

        response = HttpResponseRedirect(logout_url)
        response.delete_cookie("access_token")
        return response
