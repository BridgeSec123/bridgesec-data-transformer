from urllib.parse import quote
import logging

from django.conf import settings
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


class OktaLoginView(APIView):
    def get(self, request):
        request_id = getattr(request, 'request_id', 'N/A')

        logger.info(
            "Okta login initiated",
            extra={
                'component': 'auth',
                'request_id': request_id,
                'action': 'login',
            }
        )

        # --- Multi-tenancy: resolve tenant from ?okta_domain query param ---
        okta_domain = request.query_params.get("okta_domain")
        tenant = None
        if getattr(settings, "MULTI_TENANCY_ENABLED", False) and okta_domain:
            from core.utils.tenant_utils import get_tenant_by_okta_domain
            tenant = get_tenant_by_okta_domain(okta_domain)
            if tenant:
                # Store tenant_id in session for the callback
                request.session["tenant_id"] = str(tenant.id)
                request.session.save()
                logger.info(f"Multi-tenant login for tenant '{tenant.name}'")
            else:
                logger.warning(f"Tenant not found for okta_domain='{okta_domain}'")

        # Resolve issuer and client_id — use tenant's if available, fall back to settings
        if tenant:
            issuer_base = tenant.okta_issuer.rstrip('/')
            client_id = tenant.okta_client_id
            redirect_uri = settings.OKTA_REDIRECT_URI   # redirect URI is shared
            scopes = settings.OKTA_SCOPES
        else:
            issuer_base = settings.OKTA_ISSUER.rstrip('/')
            client_id = settings.OKTA_CLIENT_ID
            redirect_uri = settings.OKTA_REDIRECT_URI
            scopes = settings.OKTA_SCOPES

        # URL encode the scopes to handle special characters
        encoded_scopes = quote(scopes, safe='')

        # Build authorize URL - handle both org and custom auth servers
        if '/oauth2/' in issuer_base:
            # Custom authorization server (e.g., /oauth2/default)
            authorize_url = (
                f"{issuer_base}/v1/authorize?"
                f"client_id={client_id}&"
                f"response_type=code&"
                f"scope={encoded_scopes}&"
                f"redirect_uri={redirect_uri}&"
                f"state=xyz&nonce=abc&"
                f"prompt=login"
            )
        else:
            # Org authorization server
            authorize_url = (
                f"{issuer_base}/oauth2/v1/authorize?"
                f"client_id={client_id}&"
                f"response_type=code&"
                f"scope={encoded_scopes}&"
                f"redirect_uri={redirect_uri}&"
                f"state=xyz&nonce=abc&"
                f"prompt=login"
            )

        logger.info(
            "Redirecting to Okta authorization",
            extra={
                'component': 'auth',
                'request_id': request_id,
                'redirect_url': issuer_base,
            }
        )

        return Response({"authorization_url": authorize_url})


