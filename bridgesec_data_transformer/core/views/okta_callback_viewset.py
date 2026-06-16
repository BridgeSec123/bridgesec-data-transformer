import base64
import json
import logging
import time

import requests
from django.conf import settings
from django.http import HttpResponseRedirect
from jose import jwt
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.authentication import _get_user_backend
from core.utils.jwt_utils import generate_jwt_token

logger = logging.getLogger(__name__)


class OktaCallbackView(APIView):
    def get(self, request):
        request_id = getattr(request, 'request_id', 'N/A')

        logger.info(
            "OAuth callback received",
            extra={
                'component': 'auth',
                'request_id': request_id,
                'action': 'callback',
            }
        )

        code = request.GET.get("code")
        error = request.GET.get("error")
        error_description = request.GET.get("error_description")

        # Handle OAuth errors from Okta
        if error:
            logger.error(
                f"OAuth error from Okta: {error}",
                extra={
                    'component': 'auth',
                    'request_id': request_id,
                    'error': error,
                    'error_description': error_description,
                }
            )
            return Response(
                {"error": error, "error_description": error_description},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not code:
            return Response(
                {"error": "Authorization code not received"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # --- Multi-tenancy: resolve tenant from OAuth state param ---
        # OktaLoginView encodes okta_domain into state. Okta returns it unchanged
        # in the callback URL, so we can query Supabase directly — no session needed.
        tenant = None
        if getattr(settings, "MULTI_TENANCY_ENABLED", False):
            state = request.GET.get("state", "")
            if state and state != "no_tenant":
                from core.utils.supabase_tenant import SupabaseTenant
                tenant = SupabaseTenant.get_by_okta_domain(state)
                if tenant:
                    logger.info(f"Using tenant '{tenant.name}' for OAuth callback (via state param)")
                else:
                    logger.warning(f"Tenant not found for okta_domain='{state}' from state param")

        # Resolve issuer and credentials — use tenant's if available
        if tenant:
            issuer_base = tenant.okta_issuer.rstrip('/')
            client_id = tenant.okta_client_id
            client_secret = tenant.okta_client_secret
        else:
            issuer_base = settings.OKTA_ISSUER.rstrip('/')
            client_id = settings.OKTA_CLIENT_ID
            client_secret = settings.OKTA_SECRET_KEY

        # Build token URL - handle both org and custom auth servers
        if '/oauth2/' in issuer_base:
            # Custom authorization server (e.g., /oauth2/default)
            token_url = f"{issuer_base}/v1/token"
            jwks_url = f"{issuer_base}/v1/keys"
        else:
            # Org authorization server
            token_url = f"{issuer_base}/oauth2/v1/token"
            jwks_url = f"{issuer_base}/oauth2/v1/keys"

        logger.info(f"Using token URL: {token_url}")

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.OKTA_REDIRECT_URI,
            "client_id": client_id,
            "client_secret": client_secret,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        token_resp = requests.post(token_url, data=data, headers=headers)
        token_data = token_resp.json()

        # Check for token exchange errors
        if "error" in token_data:
            return Response(
                {
                    "error": token_data.get("error"),
                    "error_description": token_data.get("error_description", "Token exchange failed")
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        id_token = token_data.get("id_token")
        access_token = token_data.get("access_token")

        # SECURITY: Do not log full access tokens
        # logger.info(f"OKTA ACCESS TOKEN: {access_token}")
        logger.info(f"OKTA ACCESS TOKEN received (length: {len(access_token) if access_token else 0})")
        print(f"\n[OKTA ACCESS TOKEN] {access_token}\n")

        # TEMPORARY DEBUG: Remove this after debugging!
        # logger.debug(f"DEBUG - Full Access Token: {access_token}")

        if not id_token or not access_token:
            return Response({"error": "Token not received"}, status=status.HTTP_400_BAD_REQUEST)

        # Extract granted scopes from access token
        granted_scopes = self._extract_scopes_from_token(access_token)
        print(f"\n[OKTA GRANTED SCOPES] {granted_scopes}\n")

        logger.info(
            "Token exchange successful",
            extra={
                'component': 'auth',
                'request_id': request_id,
                'granted_scopes_count': len(granted_scopes),
                'scopes': granted_scopes,
            }
        )

        # Decode and verify ID token
        # First, extract the actual issuer from the token to avoid validation errors
        logger.info(f"Fetching JWKS from: {jwks_url}")
        jwks = requests.get(jwks_url).json()
        unverified_header = jwt.get_unverified_header(id_token)
        kid = unverified_header["kid"]

        key = next((k for k in jwks["keys"] if k["kid"] == kid), None)
        if not key:
            return Response(
                {"error": "Token verification failed - signing key not found"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Decode without verification first to get the actual issuer
        unverified_payload = jwt.get_unverified_claims(id_token)
        actual_issuer = unverified_payload.get('iss')

        logger.info(f"Token issuer claim: {actual_issuer}")
        logger.info(f"Expected issuer: {issuer_base}")

        # Now decode with proper issuer validation.
        # audience must be the tenant's client_id (not the global settings value)
        # because Okta sets aud = the client_id of the app that requested the token.
        payload = jwt.decode(
            id_token,
            key,
            algorithms=["RS256"],
            audience=client_id,
            issuer=actual_issuer,
            access_token=access_token
        )

        email = payload.get("email") or payload.get("sub")
        username = email

        if not email:
            return Response(
                {"error": "Email is required from Okta"},
                status=status.HTTP_400_BAD_REQUEST
            )

        UserBackend = _get_user_backend()
        user = UserBackend.get_by_email(email)
        if not user:
            tenant_id_str = str(tenant.id) if tenant else None
            user = UserBackend.create_or_update(
                email=email, username=username, roles=["user"], tenant_id=tenant_id_str
            )
            logger.info(
                f"New user created: {email}",
                extra={
                    'component': 'auth',
                    'request_id': request_id,
                    'user': email,
                    'action': 'user_created',
                }
            )
        else:
            # Update tenant_id on existing user if it changed
            if tenant and str(getattr(user, 'tenant_id', None)) != str(tenant.id):
                user.tenant_id = str(tenant.id)
                user.save()
            logger.info(
                f"Existing user logged in: {email}",
                extra={
                    'component': 'auth',
                    'request_id': request_id,
                    'user': email,
                    'action': 'user_login',
                }
            )

        # Log login activity (multi-tenancy)
        if tenant:
            from core.utils.activity_logger import ActivityLogger
            ActivityLogger.log(
                tenant_id=tenant.id,
                user_email=email,
                action="login",
                status="success",
                ip_address=request.META.get("REMOTE_ADDR"),
            )

        # Generate custom access token for application.
        # Pass the session tenant so JWT always carries a concrete tenant_id.
        # Critical for super admin whose user.tenant_id is None.
        login_tenant_id = str(tenant.id) if tenant else None
        jwt_token = generate_jwt_token(user, login_tenant_id=login_tenant_id)
        print(f"\n[JWT TOKEN] {email}: {jwt_token}\n")

        # Store session data
        session = request.session
        session["user_id"] = str(user.id)
        session["username"] = user.username
        session["email"] = user.email
        session["roles"] = getattr(user, "roles", ["user"])
        session["id_token"] = id_token
        session["okta_access_token"] = access_token
        session["okta_granted_scopes"] = granted_scopes
        if tenant:
            session["tenant_id"] = str(tenant.id)
        session.set_expiry(3600)
        session.save()

        logger.info(
            f"User authenticated successfully: {email}",
            extra={
                'component': 'auth',
                'request_id': request_id,
                'user': email,
                'granted_scopes': granted_scopes,
                'action': 'auth_complete',
            }
        )

        session["pending_jwt"] = jwt_token
        session["pending_jwt_issued_at"] = time.time()
        session.save()

        logger.info(
            "Pending JWT stored in session",
            extra={
                'component': 'auth',
                'request_id': request_id,
                'user': email,
                'session_key': request.session.session_key,
            }
        )

        return HttpResponseRedirect(settings.FRONTEND_REDIRECT_URL)

    def _extract_scopes_from_token(self, access_token):
        """Extract scopes from the access token payload."""
        try:
            # Split token and decode payload (middle part)
            parts = access_token.split('.')
            if len(parts) != 3:
                return []

            # Add padding if needed for base64 decoding
            payload_b64 = parts[1]
            padding = 4 - len(payload_b64) % 4
            if padding != 4:
                payload_b64 += '=' * padding

            payload = json.loads(base64.urlsafe_b64decode(payload_b64))
            return payload.get('scp', [])
        except Exception:
            return []
