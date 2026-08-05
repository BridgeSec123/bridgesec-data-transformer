"""
POST /api/okta-push/

CI/CD pipeline endpoint — applies Okta configuration changes on behalf of a tenant.

Authentication: Okta RS256 service token (Client Credentials grant).
Tenant is resolved from the token's `iss` claim via CustomJWTAuthentication.

Design decisions:
  - Never deletes: only creates and updates. Absent items in config are ignored.
  - Declarative: idempotent — safe to run on every deploy.
  - DPoP-aware: automatically uses DPoP proofs when the tenant's service app requires it.
  - Rate limited: 10 calls/min per tenant (ScopedRateThrottle, Redis-backed).
  - Every change is written to ActivityLog (audit trail).
"""
import logging

import requests
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework import status

from core.authentication import CustomJWTAuthentication
from core.permissions.decorators import require_permission
from core.utils.okta_push_validators import validate_push_payload
from core.utils.supabase_activity_log import SupabaseActivityLog
from core.utils.tenant_service_token import (
    get_service_access_token_for_tenant,
    generate_dpop_proof,
)

logger = logging.getLogger(__name__)


def _okta_base(tenant) -> str:
    domain = (getattr(tenant, "okta_domain", None) or "").rstrip("/")
    if not domain.startswith("http"):
        domain = f"https://{domain}"
    return f"{domain}/api/v1"


def _okta_request(
    method: str,
    url: str,
    token: str,
    use_dpop: bool,
    dpop_key=None,
    **kwargs,
) -> requests.Response:
    """
    Make a single Okta API call.

    When use_dpop=True: sends Authorization: DPoP <token> + a fresh DPoP proof
    header. `dpop_key` must be the same EC key used during token acquisition —
    Okta binds the token to that key (cnf.jkt) and rejects proofs from any
    other key.

    Handles the optional server nonce flow (RFC 9449 §8): if Okta responds with
    400 + use_dpop_nonce, the request is retried once with the DPoP-Nonce value
    embedded in the proof. Okta Preview orgs commonly require this for both the
    token endpoint AND resource server calls.

    When use_dpop=False: sends Authorization: Bearer <token>.
    """
    base_headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    if not use_dpop:
        return requests.request(
            method, url,
            headers={**base_headers, "Authorization": f"Bearer {token}"},
            **kwargs,
        )

    nonce = None
    for attempt in range(2):
        headers = {
            **base_headers,
            "Authorization": f"DPoP {token}",
            # ath (access token hash) is required for resource server calls per RFC 9449 §4.2
            "DPoP": generate_dpop_proof(method.upper(), url, nonce=nonce, private_key=dpop_key, access_token=token),
        }
        response = requests.request(method, url, headers=headers, **kwargs)

        if (
            response.status_code == 400
            and attempt == 0
            and "use_dpop_nonce" in (response.text or "")
        ):
            nonce = response.headers.get("DPoP-Nonce")
            if nonce:
                logger.debug(f"Okta requires DPoP nonce for {method} {url}, retrying.")
                continue

        break

    return response


def _get_service_token(tenant) -> tuple:
    """
    Obtain an Okta service token for this tenant.

    Tries plain Bearer first. If Okta rejects with invalid_dpop_proof
    (app has DPoP required), retries automatically with DPoP enabled.

    Returns:
        (access_token: str, use_dpop: bool, dpop_key: EC key object or None)
        dpop_key is the EC key bound to the token — must be reused for every
        subsequent API call with this token when use_dpop=True.
    """
    try:
        token, _, dpop_key = get_service_access_token_for_tenant(tenant, use_dpop=False)
        return token, False, None
    except ValueError as e:
        if "dpop" in str(e).lower():
            logger.info(
                f"Tenant '{tenant.name}' requires DPoP — retrying token request with DPoP."
            )
            token, _, dpop_key = get_service_access_token_for_tenant(tenant, use_dpop=True)
            return token, True, dpop_key
        raise


# ── Scope sync ────────────────────────────────────────────────────────────────

def _sync_scopes(
    base_url: str, token: str, use_dpop: bool, auth_server_id: str, desired: list,
    dpop_key=None,
) -> list:
    """Create or update scopes. Never deletes."""
    results = []

    resp = _okta_request(
        "GET",
        f"{base_url}/authorizationServers/{auth_server_id}/scopes",
        token, use_dpop, dpop_key, timeout=30,
    )
    if not resp.ok:
        return [{"entity": "scope", "action": "fetch_failed",
                 "status": "error", "detail": resp.text}]

    existing = {s["name"]: s for s in resp.json()}

    for scope in desired:
        name = scope["name"]
        payload = {
            "name": name,
            "description": scope.get("description", ""),
            "consent": scope.get("consent", "IMPLICIT"),
            "default": scope.get("default", False),
            "metadataPublish": scope.get("metadataPublish", "NO_CLIENTS"),
        }

        if name in existing:
            current = existing[name]
            changed = any(
                current.get(k) != payload[k]
                for k in ("description", "consent", "default")
            )
            if not changed:
                results.append({"entity": "scope", "name": name, "action": "unchanged"})
                continue
            r = _okta_request(
                "PUT",
                f"{base_url}/authorizationServers/{auth_server_id}/scopes/{current['id']}",
                token, use_dpop, dpop_key, json=payload, timeout=30,
            )
            action = "updated"
        else:
            r = _okta_request(
                "POST",
                f"{base_url}/authorizationServers/{auth_server_id}/scopes",
                token, use_dpop, dpop_key, json=payload, timeout=30,
            )
            action = "created"

        if r.ok:
            results.append({"entity": "scope", "name": name, "action": action,
                             "okta_id": r.json().get("id"), "status": "success"})
        else:
            results.append({"entity": "scope", "name": name, "action": action,
                             "status": "error", "detail": r.text})

    return results


# ── App sync ──────────────────────────────────────────────────────────────────

def _sync_app(
    base_url: str, token: str, use_dpop: bool, app_id: str | None, desired: dict,
    dpop_key=None,
) -> list:
    """Create app if no app_id given, otherwise update redirect_uris and settings."""
    results = []

    oauth_client = {
        "redirect_uris": desired.get("redirect_uris", []),
        "grant_types": desired.get("grant_types", ["authorization_code"]),
        "response_types": desired.get("response_types", ["code"]),
        "application_type": desired.get("application_type", "web"),
    }
    if "post_logout_redirect_uris" in desired:
        oauth_client["post_logout_redirect_uris"] = desired["post_logout_redirect_uris"]

    if not app_id:
        label = desired.get("label", "")
        payload = {
            "name": "oidc_client",
            "label": label,
            "signOnMode": "OPENID_CONNECT",
            "settings": {"oauthClient": oauth_client},
        }
        if "credentials" in desired:
            payload["credentials"] = desired["credentials"]

        # Guard: check if an app with this label already exists.
        search = _okta_request(
            "GET",
            f"{base_url}/apps",
            token, use_dpop, dpop_key,
            params={"q": label, "filter": 'status eq "ACTIVE"'},
            timeout=30,
        )
        if search.ok:
            existing_apps = [a for a in search.json() if a.get("label") == label]
            if existing_apps:
                results.append({"entity": "app", "label": label, "action": "unchanged",
                                 "okta_id": existing_apps[0]["id"],
                                 "detail": "app already exists with this label"})
                return results

        r = _okta_request(
            "POST", f"{base_url}/apps",
            token, use_dpop, dpop_key, json=payload, timeout=30,
        )
        if r.ok:
            results.append({"entity": "app", "label": label, "action": "created",
                             "okta_id": r.json().get("id"), "status": "success"})
        else:
            results.append({"entity": "app", "label": label, "action": "created",
                             "status": "error", "detail": r.text})
        return results

    # Update existing app.
    fetch = _okta_request(
        "GET", f"{base_url}/apps/{app_id}",
        token, use_dpop, dpop_key, timeout=30,
    )
    if not fetch.ok:
        return [{"entity": "app", "app_id": app_id, "action": "fetch_failed",
                 "status": "error", "detail": fetch.text or f"HTTP {fetch.status_code}"}]

    current_settings = fetch.json().get("settings", {}).get("oauthClient", {})
    current_uris = set(current_settings.get("redirect_uris") or [])
    desired_uris = set(oauth_client["redirect_uris"])

    if current_uris == desired_uris and "label" not in desired:
        results.append({"entity": "app", "app_id": app_id, "action": "unchanged"})
        return results

    current_app = fetch.json()
    current_app.setdefault("settings", {})["oauthClient"] = {
        **current_settings,
        **oauth_client,
    }
    if "label" in desired:
        current_app["label"] = desired["label"]

    r = _okta_request(
        "PUT", f"{base_url}/apps/{app_id}",
        token, use_dpop, dpop_key, json=current_app, timeout=30,
    )
    if r.ok:
        results.append({"entity": "app", "app_id": app_id, "action": "updated", "status": "success"})
    else:
        results.append({"entity": "app", "app_id": app_id, "action": "updated",
                        "status": "error", "detail": r.text})

    return results


# ── Group sync ────────────────────────────────────────────────────────────────

def _sync_groups(
    base_url: str, token: str, use_dpop: bool, app_id: str | None, desired: list,
    dpop_key=None,
) -> list:
    """Create or update groups. Assign to app if app_id provided. Never deletes."""
    results = []

    for group in desired:
        name = group["name"]
        profile = {
            "name": name,
            "description": group.get("description", ""),
        }

        search = _okta_request(
            "GET", f"{base_url}/groups",
            token, use_dpop, dpop_key, params={"q": name}, timeout=30,
        )
        if not search.ok:
            results.append({"entity": "group", "name": name, "action": "fetch_failed",
                             "status": "error", "detail": search.text})
            continue

        matches = [g for g in search.json() if g.get("profile", {}).get("name") == name]

        if matches:
            existing = matches[0]
            current_profile = existing.get("profile", {})
            if current_profile.get("description") == profile["description"]:
                results.append({"entity": "group", "name": name, "action": "unchanged",
                                 "okta_id": existing["id"]})
            else:
                r = _okta_request(
                    "PUT", f"{base_url}/groups/{existing['id']}",
                    token, use_dpop, dpop_key, json={"profile": profile}, timeout=30,
                )
                if r.ok:
                    results.append({"entity": "group", "name": name, "action": "updated",
                                    "okta_id": existing["id"], "status": "success"})
                else:
                    results.append({"entity": "group", "name": name, "action": "updated",
                                    "status": "error", "detail": r.text})
            group_id = existing["id"]
        else:
            r = _okta_request(
                "POST", f"{base_url}/groups",
                token, use_dpop, dpop_key, json={"profile": profile}, timeout=30,
            )
            if r.ok:
                group_id = r.json().get("id")
                results.append({"entity": "group", "name": name, "action": "created",
                                 "okta_id": group_id, "status": "success"})
            else:
                results.append({"entity": "group", "name": name, "action": "created",
                                 "status": "error", "detail": r.text})
                continue

        # Assign to app if app_id provided.
        if app_id and group_id:
            assign = _okta_request(
                "PUT", f"{base_url}/apps/{app_id}/groups/{group_id}",
                token, use_dpop, dpop_key, json={}, timeout=30,
            )
            if not assign.ok and assign.status_code != 409:
                results.append({"entity": "group_assignment", "name": name,
                                 "app_id": app_id, "status": "error", "detail": assign.text})

    return results


# ── Policy sync ───────────────────────────────────────────────────────────────

def _sync_policies(
    base_url: str, token: str, use_dpop: bool, app_id: str | None, desired: list,
    dpop_key=None,
) -> list:
    """Create or update policies and their rules. Never deletes."""
    results = []

    for policy in desired:
        policy_name = policy["name"]
        policy_type = policy.get("type", "OKTA_SIGN_ON")

        fetch = _okta_request(
            "GET", f"{base_url}/policies",
            token, use_dpop, dpop_key, params={"type": policy_type}, timeout=30,
        )
        if not fetch.ok:
            results.append({"entity": "policy", "name": policy_name, "action": "fetch_failed",
                             "status": "error", "detail": fetch.text})
            continue

        existing_policies = [p for p in fetch.json() if p.get("name") == policy_name]

        if existing_policies:
            policy_id = existing_policies[0]["id"]
            results.append({"entity": "policy", "name": policy_name,
                             "action": "unchanged", "okta_id": policy_id})
        else:
            payload = {
                "name": policy_name,
                "type": policy_type,
                "status": "ACTIVE",
                "description": policy.get("description", ""),
                "conditions": policy.get("conditions", {}),
            }
            r = _okta_request(
                "POST", f"{base_url}/policies",
                token, use_dpop, dpop_key, json=payload, timeout=30,
            )
            if not r.ok:
                results.append({"entity": "policy", "name": policy_name, "action": "created",
                                 "status": "error", "detail": r.text})
                continue
            policy_id = r.json().get("id")
            results.append({"entity": "policy", "name": policy_name, "action": "created",
                             "okta_id": policy_id, "status": "success"})
            if app_id:
                _okta_request(
                    "PUT", f"{base_url}/apps/{app_id}/policies/{policy_id}",
                    token, use_dpop, dpop_key, json={}, timeout=30,
                )

        # Sync rules within this policy.
        rules_fetch = _okta_request(
            "GET", f"{base_url}/policies/{policy_id}/rules",
            token, use_dpop, dpop_key, timeout=30,
        )
        existing_rules = {
            r["name"]: r
            for r in (rules_fetch.json() if rules_fetch.ok else [])
        }

        for rule in policy.get("rules") or []:
            rule_name = rule["name"]
            rule_payload = {
                "name": rule_name,
                "type": "SIGN_ON",
                "conditions": rule.get("conditions", {}),
                "actions": rule.get("actions", {}),
            }
            if rule_name in existing_rules:
                rule_id = existing_rules[rule_name]["id"]
                r = _okta_request(
                    "PUT", f"{base_url}/policies/{policy_id}/rules/{rule_id}",
                    token, use_dpop, dpop_key, json=rule_payload, timeout=30,
                )
                action = "updated"
            else:
                r = _okta_request(
                    "POST", f"{base_url}/policies/{policy_id}/rules",
                    token, use_dpop, dpop_key, json=rule_payload, timeout=30,
                )
                action = "created"

            if r.ok:
                results.append({"entity": "policy_rule", "name": rule_name,
                                 "policy": policy_name, "action": action,
                                 "okta_id": r.json().get("id"), "status": "success"})
            else:
                results.append({"entity": "policy_rule", "name": rule_name,
                                 "policy": policy_name, "action": action,
                                 "status": "error", "detail": r.text})

    return results


def _sync_app_config(base_url: str, token: str, use_dpop: bool, config: dict, dpop_key=None) -> list:
    """Run scope/app/group/policy sync for a single app config. Returns list of changes."""
    auth_server_id = config.get("auth_server_id")
    app_id = config.get("app_id")

    changes = []
    if config.get("scopes") and auth_server_id:
        changes.extend(_sync_scopes(base_url, token, use_dpop, auth_server_id, config["scopes"], dpop_key=dpop_key))
    if config.get("app"):
        changes.extend(_sync_app(base_url, token, use_dpop, app_id, config["app"], dpop_key=dpop_key))
    if config.get("groups"):
        changes.extend(_sync_groups(base_url, token, use_dpop, app_id, config["groups"], dpop_key=dpop_key))
    if config.get("policies"):
        changes.extend(_sync_policies(base_url, token, use_dpop, app_id, config["policies"], dpop_key=dpop_key))
    return changes


def _summarize(changes: list) -> dict:
    return {
        "created": sum(1 for c in changes if c.get("action") == "created"),
        "updated": sum(1 for c in changes if c.get("action") == "updated"),
        "unchanged": sum(1 for c in changes if c.get("action") == "unchanged"),
        "errors": sum(1 for c in changes if c.get("status") == "error"),
    }


# ── View ──────────────────────────────────────────────────────────────────────

class OktaPushView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    # Authorization via the global RolePermission gate (@require_permission("okta_push")).
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "okta_push"
    entity_type = "okta_push"

    @require_permission("okta_push")
    def post(self, request):
        tenant = getattr(request, "_tenant", None)
        if not tenant:
            return Response(
                {"error": "Tenant could not be resolved from token"},
                status=status.HTTP_403_FORBIDDEN,
            )

        data = request.data
        if not isinstance(data, dict):
            return Response({"error": "Request body must be a JSON object"},
                            status=status.HTTP_400_BAD_REQUEST)

        validation_errors = validate_push_payload(data)
        if validation_errors:
            return Response({"errors": validation_errors},
                            status=status.HTTP_400_BAD_REQUEST)

        # Obtain a service token — auto-detects whether DPoP is required.
        # dpop_key is the EC key bound to the token; must be reused for all API calls.
        try:
            service_token, use_dpop, dpop_key = _get_service_token(tenant)
        except ValueError as e:
            logger.error(f"okta-push: failed to get service token for tenant {tenant.id}: {e}")
            return Response({"error": "Could not obtain Okta service token", "detail": str(e)},
                            status=status.HTTP_502_BAD_GATEWAY)

        base_url = _okta_base(tenant)
        apps_payload = data.get("apps")

        if apps_payload is not None:
            return self._handle_bulk(request, tenant, base_url, service_token, use_dpop, dpop_key, apps_payload)
        return self._handle_single(request, tenant, base_url, service_token, use_dpop, dpop_key, data)

    def _handle_single(self, request, tenant, base_url, service_token, use_dpop, dpop_key, data):
        auth_server_id = data.get("auth_server_id")
        app_id = data.get("app_id")

        all_changes = _sync_app_config(base_url, service_token, use_dpop, data, dpop_key=dpop_key)
        errors = [c for c in all_changes if c.get("status") == "error"]
        summary = _summarize(all_changes)

        SupabaseActivityLog.log(
            user_email=getattr(request.user, "email", "unknown"),
            action="okta_push",
            tenant_id=str(tenant.id),
            entity_name="okta_config",
            status="error" if errors else "success",
            ip_address=request.META.get("REMOTE_ADDR"),
            details={
                "auth_server_id": auth_server_id,
                "app_id": app_id,
                "use_dpop": use_dpop,
                "summary": summary,
                "changes": all_changes,
            },
        )

        http_status = status.HTTP_207_MULTI_STATUS if errors else status.HTTP_200_OK
        return Response(
            {
                "tenant_id": str(tenant.id),
                "auth_server_id": auth_server_id,
                "app_id": app_id,
                "summary": summary,
                "changes": all_changes,
                "errors": errors,
            },
            status=http_status,
        )

    def _handle_bulk(self, request, tenant, base_url, service_token, use_dpop, dpop_key, apps_payload):
        results = []
        all_changes = []

        for config in apps_payload:
            auth_server_id = config.get("auth_server_id")
            app_id = config.get("app_id")

            changes = _sync_app_config(base_url, service_token, use_dpop, config, dpop_key=dpop_key)
            app_errors = [c for c in changes if c.get("status") == "error"]
            summary = _summarize(changes)
            all_changes.extend(changes)

            SupabaseActivityLog.log(
                user_email=getattr(request.user, "email", "unknown"),
                action="okta_push",
                tenant_id=str(tenant.id),
                entity_name="okta_config",
                status="error" if app_errors else "success",
                ip_address=request.META.get("REMOTE_ADDR"),
                details={
                    "auth_server_id": auth_server_id,
                    "app_id": app_id,
                    "use_dpop": use_dpop,
                    "summary": summary,
                    "changes": changes,
                },
            )

            results.append({
                "app_id": app_id,
                "auth_server_id": auth_server_id,
                "summary": summary,
                "changes": changes,
                "errors": app_errors,
            })

        summary = _summarize(all_changes)
        http_status = status.HTTP_207_MULTI_STATUS if summary["errors"] else status.HTTP_200_OK
        return Response(
            {
                "tenant_id": str(tenant.id),
                "results": results,
                "summary": summary,
            },
            status=http_status,
        )
