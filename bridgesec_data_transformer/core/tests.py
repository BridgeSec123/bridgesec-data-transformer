from unittest.mock import patch

from django.test import SimpleTestCase
from jose import jwt

from core.permissions.rbac_permission import RolePermission
from core.utils.tenant_service_token import generate_dpop_proof


class _User:
    def __init__(self, roles, authed=True):
        self.roles = roles
        self.is_authenticated = authed


class _QP(dict):
    def get(self, k, d=""):
        return super().get(k, d)


class _Req:
    def __init__(self, path, method, roles, qp=None, authed=True):
        self.path, self.method = path, method
        self.user = _User(roles, authed)
        self.query_params = _QP(qp or {})


class _View:
    def __init__(self, entity_type=None, rbac_exempt=False, kwargs=None):
        if entity_type:
            self.entity_type = entity_type
        self.rbac_exempt = rbac_exempt
        self.kwargs = kwargs or {}


_TEST_ROLE_PERMS = {
    "super_admin": {"view_tenants", "create_tenant"},
    "tenant_admin": {"trigger_bulk_fetch", "view_db_map", "restore_data"},
    "user": {"view_db_map"},
}


def _fake_get_permissions_for_roles(roles):
    return set().union(*(_TEST_ROLE_PERMS.get(r, set()) for r in (roles or []))) if roles else set()


def _decorated_view(method_name, required_permission, action=None):
    class _V:
        pass
    v = _V()
    if action:
        v.action = action

    def handler(*a, **k):
        pass
    handler.required_permission = required_permission
    setattr(v, method_name, handler)
    return v


class RolePermissionGateTests(SimpleTestCase):
    """New DB-backed RBAC gate. get_permissions_for_roles is mocked to a fixed
    role->permissions map so this stays network-free, like IniRBACGateTests
    above — the real function is exercised separately against live Supabase
    data via the role-permission API endpoints."""

    def setUp(self):
        self.gate = RolePermission()
        patcher = patch(
            "core.permissions.rbac_permission.get_permissions_for_roles",
            side_effect=_fake_get_permissions_for_roles,
        )
        self.addCleanup(patcher.stop)
        patcher.start()

    def test_allows_role_with_permission(self):
        view = _decorated_view("post", "trigger_bulk_fetch")
        req = _Req("/api/bulk/", "POST", ["tenant_admin"])
        self.assertTrue(self.gate.has_permission(req, view))

    def test_denies_role_without_permission(self):
        view = _decorated_view("post", "trigger_bulk_fetch")
        req = _Req("/api/bulk/", "POST", ["user"])
        self.assertFalse(self.gate.has_permission(req, view))

    def test_undecorated_handler_denies_by_default(self):
        class _V:
            def post(self, *a, **k):
                pass
        req = _Req("/api/something/", "POST", ["super_admin"])
        self.assertFalse(self.gate.has_permission(req, _V()))

    def test_rbac_exempt_bypasses(self):
        req = _Req("/api/tenants/x/logo/", "GET", ["user"])
        self.assertTrue(self.gate.has_permission(req, _View(rbac_exempt=True)))

    def test_bypass_paths_allow_unauthenticated(self):
        req = _Req("/okta/login/", "GET", [], authed=False)
        self.assertTrue(self.gate.has_permission(req, _View()))

    def test_unauthenticated_denied_on_protected_route(self):
        view = _decorated_view("get", "view_tenants")
        req = _Req("/api/tenants/", "GET", [], authed=False)
        self.assertFalse(self.gate.has_permission(req, view))

    def test_viewset_action_resolution(self):
        # DRF sets view.action (not request.method) for ViewSet-based routes
        # like BulkEntityViewSet's .as_view({"post": "restore_modified_data"}).
        view = _decorated_view("restore_modified_data", "restore_data", action="restore_modified_data")
        req = _Req("/restore/db/entity/", "POST", ["tenant_admin"])
        self.assertTrue(self.gate.has_permission(req, view))
        req_denied = _Req("/restore/db/entity/", "POST", ["user"])
        self.assertFalse(self.gate.has_permission(req_denied, view))


class DpopProofHtuTests(SimpleTestCase):
    """RFC 9449 §4.2: htu must drop query/fragment — Okta 400s (invalid_dpop_proof)
    otherwise on any request with a query string (pagination, filters, etc.)."""

    def test_htu_strips_query_and_fragment(self):
        proof = generate_dpop_proof("GET", "https://tenant.okta.com/api/v1/users?limit=5&after=x#frag")
        claims = jwt.get_unverified_claims(proof)
        self.assertEqual(claims["htu"], "https://tenant.okta.com/api/v1/users")

    def test_htu_unchanged_without_query(self):
        proof = generate_dpop_proof("GET", "https://tenant.okta.com/api/v1/org")
        claims = jwt.get_unverified_claims(proof)
        self.assertEqual(claims["htu"], "https://tenant.okta.com/api/v1/org")


class _ScopeSession:
    def __init__(self, scopes=None):
        self._scopes = scopes or []

    def get(self, key, default=None):
        if key == "okta_granted_scopes":
            return self._scopes
        return default


class _ScopeRequest:
    def __init__(self, tenant=None, tenant_id=None, scopes=None):
        self._tenant = tenant
        self._tenant_id = tenant_id
        self.session = _ScopeSession(scopes)


class ScopeValidationTests(SimpleTestCase):
    def test_prefers_tenant_scopes_over_session_scopes(self):
        from core.utils.okta_helpers import validate_scope_for_endpoint

        tenant = type("Tenant", (), {"service_scopes": "okta.users.read okta.groups.read"})()
        request = _ScopeRequest(tenant=tenant, scopes=["okta.apps.read"])

        is_valid, required, granted, missing = validate_scope_for_endpoint(request, "https://example.okta.com/api/v1/users")

        self.assertTrue(required)
        self.assertEqual(granted, ["okta.users.read", "okta.groups.read"])
        self.assertIsInstance(is_valid, bool)
        self.assertIsInstance(missing, list)

    @patch("core.utils.okta_helpers.settings")
    @patch("core.utils.okta_helpers.get_tenant_by_id")
    def test_falls_back_to_tenant_lookup_from_tenant_id(self, mock_get_tenant, mock_settings):
        from core.utils.okta_helpers import validate_scope_for_endpoint

        mock_settings.MULTI_TENANCY_ENABLED = True
        tenant = type("Tenant", (), {"service_scopes": "okta.users.read"})()
        mock_get_tenant.return_value = tenant

        request = _ScopeRequest(tenant=None, tenant_id="tenant-123", scopes=["okta.apps.read"])

        _, _, granted, _ = validate_scope_for_endpoint(request, "https://example.okta.com/api/v1/users")

        self.assertEqual(granted, ["okta.users.read"])
