from urllib.parse import quote
import logging

from django.conf import settings
from django.http import HttpResponseRedirect
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

        # force_login=true → adds prompt=login to Okta URL (initial sign-in only).
        # Tenant switches omit this so Okta SSO session handles re-auth silently.
        force_login = request.query_params.get("force_login", "").lower() == "true"

        # --- Multi-tenancy: resolve tenant from ?okta_domain query param ---
        # okta_domain is encoded into the OAuth state param so the callback
        # can look it up from Supabase directly — no session dependency.
        okta_domain = request.query_params.get("okta_domain")
        tenant = None
        if getattr(settings, "MULTI_TENANCY_ENABLED", False) and okta_domain:
            from core.utils.tenant_utils import get_tenant_by_okta_domain
            tenant = get_tenant_by_okta_domain(okta_domain)
            if tenant:
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

        prompt_param = "&prompt=login" if force_login else ""

        # Encode okta_domain into state so the callback can resolve the tenant
        # from Supabase without needing the session to survive the Okta redirect.
        state = okta_domain if okta_domain else "no_tenant"

        # Pre-fill the Okta username field so the user lands directly on the password page
        # (requires Identifier First flow enabled on the Okta tenant).
        login_hint = request.query_params.get("login_hint", "")
        login_hint_param = f"&login_hint={quote(login_hint, safe='')}" if login_hint else ""

        # Build authorize URL - handle both org and custom auth servers
        if '/oauth2/' in issuer_base:
            # Custom authorization server (e.g., /oauth2/default)
            authorize_url = (
                f"{issuer_base}/v1/authorize?"
                f"client_id={client_id}&"
                f"response_type=code&"
                f"scope={encoded_scopes}&"
                f"redirect_uri={redirect_uri}&"
                f"state={state}&nonce=abc"
                f"{prompt_param}"
                f"{login_hint_param}"
            )
        else:
            # Org authorization server
            authorize_url = (
                f"{issuer_base}/oauth2/v1/authorize?"
                f"client_id={client_id}&"
                f"response_type=code&"
                f"scope={encoded_scopes}&"
                f"redirect_uri={redirect_uri}&"
                f"state={state}&nonce=abc"
                f"{prompt_param}"
                f"{login_hint_param}"
            )

        logger.info(
            "Redirecting to Okta authorization",
            extra={
                'component': 'auth',
                'request_id': request_id,
                'redirect_url': issuer_base,
            }
        )

        return HttpResponseRedirect(authorize_url)


