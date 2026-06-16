import logging
import types
import uuid

from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.authentication import CustomJWTAuthentication
from core.serializers.policy_serializer import PolicyRuleSerializer
from core.services import opa_client, opa_sync, rego_builder

_OPA_TAG = ["OPA Policy Management"]

logger = logging.getLogger(__name__)


class PolicyViewSet(viewsets.ViewSet):
    """CRUD + resync + dry-run for OPA policies (Supabase-backed).

    Protected by `IsAuthenticated` only — self-management must not depend on
    OPA having any policies loaded (chicken-and-egg). `/api/policies/` is
    also listed in OPAPermission's `OPA_BYPASS_PATHS` as defense in depth.
    """

    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    entity_type = "policies"

    def _is_super_admin(self, request) -> bool:
        return "super_admin" in (getattr(request.user, "roles", None) or [])

    def _caller_tenant_id(self, request):
        """Return the tenant scope for policy management.

        - super_admin: ?tenant_id=X authors/lists for that tenant; absent → global (None).
        - everyone else: the JWT-scoped active tenant (request._tenant_id), falling back
          to the user's home tenant. A user can belong to several tenants, so the active
          tenant — not the global users.tenant_id — is authoritative.
        """
        if self._is_super_admin(request):
            return request.query_params.get("tenant_id") or None
        return (
            getattr(request, "_tenant_id", None)
            or (str(getattr(request.user, "tenant_id", "") or "") or None)
        )

    def _get_or_404(self, pk):
        from core.utils.supabase_policy import SupabasePolicyRule
        rule = SupabasePolicyRule.get_by_id(pk)
        if not rule:
            raise NotFound(f"Policy '{pk}' not found.")
        return rule

    def _assert_can_modify(self, request, rule):
        """Raise PermissionDenied if a non-super-admin tries to touch another tenant's rule."""
        if self._is_super_admin(request):
            return
        caller_tid = self._caller_tenant_id(request)
        if rule.tenant_id and rule.tenant_id != caller_tid:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only modify policies that belong to your tenant.")

    def _assert_can_read(self, request, rule):
        """Raise PermissionDenied if a non-super-admin tries to read another tenant's rule."""
        if self._is_super_admin(request):
            return
        caller_tid = self._caller_tenant_id(request)
        if rule.tenant_id and rule.tenant_id != caller_tid:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only view policies that belong to your tenant.")

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    @swagger_auto_schema(tags=_OPA_TAG)
    def list(self, request):
        from core.utils.supabase_policy import SupabasePolicyRule
        role_filter = request.query_params.get("role")
        try:
            page      = max(1, int(request.query_params.get("page", 1)))
            page_size = min(200, max(1, int(request.query_params.get("page_size", 50))))
        except ValueError:
            page, page_size = 1, 50
        # Non-super-admin callers see global + their own tenant's policies only
        tenant_id = self._caller_tenant_id(request)
        rules, total = SupabasePolicyRule.list_all(
            role=role_filter, page=page, page_size=page_size, tenant_id=tenant_id
        )
        data = [PolicyRuleSerializer(r, context={"request": request}).to_representation(r) for r in rules]
        return Response({"total": total, "page": page, "page_size": page_size, "results": data})

    @swagger_auto_schema(tags=_OPA_TAG)
    def create(self, request):
        ser = PolicyRuleSerializer(data=request.data, context={"request": request})
        ser.is_valid(raise_exception=True)

        body_tenant_id = ser.validated_data.get("tenant_id")
        caller_tenant_id = self._caller_tenant_id(request)

        if body_tenant_id and not self._is_super_admin(request):
            if str(body_tenant_id) != str(caller_tenant_id or ""):
                return Response(
                    {"error": "You can only create policies for your own tenant."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        resolved_tenant_id = body_tenant_id or caller_tenant_id
        rule = ser.save(tenant_id=resolved_tenant_id)
        try:
            opa_client.push_policy(str(rule.id), rule.rego_source)
        except Exception as e:
            from core.utils.supabase_policy import SupabasePolicyRule
            SupabasePolicyRule.delete(str(rule.id))
            logger.exception("Failed to push new policy to OPA; rolled back Supabase insert")
            return Response(
                {"error": "Failed to push policy to OPA.", "detail": str(e)},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return Response(
            PolicyRuleSerializer(rule, context={"request": request}).to_representation(rule),
            status=status.HTTP_201_CREATED,
        )

    @swagger_auto_schema(tags=_OPA_TAG)
    def retrieve(self, request, pk=None):
        rule = self._get_or_404(pk)
        self._assert_can_read(request, rule)
        return Response(PolicyRuleSerializer(rule, context={"request": request}).to_representation(rule))

    @swagger_auto_schema(tags=_OPA_TAG)
    def update(self, request, pk=None):
        rule = self._get_or_404(pk)
        self._assert_can_modify(request, rule)
        ser = PolicyRuleSerializer(rule, data=request.data, context={"request": request})
        ser.is_valid(raise_exception=True)
        rule = ser.save()
        opa_client.push_policy(str(rule.id), rule.rego_source)
        return Response(PolicyRuleSerializer(rule, context={"request": request}).to_representation(rule))

    @swagger_auto_schema(tags=_OPA_TAG)
    def partial_update(self, request, pk=None):
        rule = self._get_or_404(pk)
        self._assert_can_modify(request, rule)
        ser = PolicyRuleSerializer(rule, data=request.data, partial=True, context={"request": request})
        ser.is_valid(raise_exception=True)
        rule = ser.save()
        opa_client.push_policy(str(rule.id), rule.rego_source)
        return Response(PolicyRuleSerializer(rule, context={"request": request}).to_representation(rule))

    @swagger_auto_schema(tags=_OPA_TAG)
    def destroy(self, request, pk=None):
        rule = self._get_or_404(pk)
        self._assert_can_modify(request, rule)
        try:
            opa_client.delete_policy(str(rule.id))
        except Exception as e:
            logger.warning("Failed to delete policy from OPA; deleting Supabase record anyway",
                           extra={"policy_id": str(rule.id), "error": str(e)})
        from core.utils.supabase_policy import SupabasePolicyRule
        SupabasePolicyRule.delete(str(rule.id))
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ------------------------------------------------------------------
    # Extra actions
    # ------------------------------------------------------------------
    @swagger_auto_schema(tags=_OPA_TAG)
    @action(detail=False, methods=["post"], url_path="resync")
    def resync(self, request):
        result = opa_sync.sync_from_mongo()
        return Response({
            "synced": result["synced"],
            "removed_orphans": result["removed_orphans"],
            "message": "Sync complete" if not result.get("skipped") else "OPA unreachable; sync skipped",
        })

    @swagger_auto_schema(tags=_OPA_TAG)
    @action(detail=False, methods=["post"], url_path="test")
    def test(self, request):
        """Dry-run: translate a candidate rule + evaluate against provided input."""
        rule_data   = request.data.get("rule") or {}
        sample_input = request.data.get("input") or {}

        ser = PolicyRuleSerializer(data=rule_data, context={"request": request})
        ser.is_valid(raise_exception=True)

        rule_obj = types.SimpleNamespace(
            policy_id=f"test_{uuid.uuid4().hex[:8]}",
            **ser.validated_data,
        )
        rego_text = rego_builder.translate(rule_obj)

        try:
            opa_client.push_policy("__dry_run__", rego_text)
            decision = opa_client.query(sample_input)
        finally:
            try:
                opa_client.delete_policy("__dry_run__")
            except Exception:
                pass

        return Response({
            "decision": decision,
            "generated_rego": rego_text,
            "persisted": False,
        })


class UserRoleUpdateView(APIView):
    """PATCH /api/users/<id>/role/ — legacy single-role update (deprecated in favour of /roles/ endpoints)."""

    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    entity_type = "users"
    http_method_names = ["patch", "options"]

    @swagger_auto_schema(tags=_OPA_TAG)
    def patch(self, request, pk=None):
        if "super_admin" not in (getattr(request.user, "roles", None) or []):
            return Response(
                {"detail": "Super-admin access required."},
                status=status.HTTP_403_FORBIDDEN,
            )

        new_role = request.data.get("role")
        if not new_role:
            raise ValidationError({"role": "This field is required."})

        from core.authentication import _get_user_backend
        UserBackend = _get_user_backend()
        user = UserBackend.get_by_id(pk)
        if not user:
            raise NotFound(f"User '{pk}' not found.")

        current_roles = list(user.roles or ["user"])
        if new_role not in current_roles:
            current_roles.append(new_role)
        UserBackend.update_roles(str(user.id), current_roles)
        user.roles = current_roles
        return Response({
            "id":     str(user.id),
            "email":  user.email,
            "roles":  user.roles,
        })
