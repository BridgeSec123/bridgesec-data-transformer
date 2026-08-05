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
        tenant_id = request.session.get("tenant_id")

        logger.info(
            f"User logout initiated: {user_email}",
            extra={
                'component': 'auth',
                'request_id': request_id,
                'user': user_email,
                'action': 'logout',
            }
        )

        redirect_url = f"{settings.FRONTEND_URL}/sign-in"

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

        # Resolve okta_issuer from Supabase tenant record (multi-tenant primary path)
        okta_issuer = None
        if tenant_id:
            from core.utils.supabase_tenant import SupabaseTenant
            tenant = SupabaseTenant.get_by_id(str(tenant_id))
            if tenant and tenant.okta_issuer:
                okta_issuer = tenant.okta_issuer.rstrip('/')

        # Fallback: settings.OKTA_ISSUER for single-tenant / dev mode
        if not okta_issuer:
            fallback = getattr(settings, 'OKTA_ISSUER', None)
            if fallback:
                okta_issuer = fallback.rstrip('/')

        if not okta_issuer:
            logger.warning(
                f"No okta_issuer resolved for tenant {tenant_id}; performing soft logout",
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

        logout_url = (
            f"{okta_issuer}/v1/logout?"
            f"id_token_hint={id_token}&"
            f"post_logout_redirect_uri={redirect_url}"
        )

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
