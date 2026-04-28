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
from core.models.policy_models import PolicyRule
from core.models.user import User
from core.serializers.policy_serializer import PolicyRuleSerializer
from core.services import opa_client, opa_sync, rego_builder

_OPA_TAG = ["OPA Policy Management"]

logger = logging.getLogger(__name__)


class PolicyViewSet(viewsets.ViewSet):
    """CRUD + resync + dry-run for OPA policies.

    Protected by `IsAuthenticated` only — self-management must not depend on
    OPA having any policies loaded (chicken-and-egg). `/api/policies/` is
    also listed in OPAPermission's `OPA_BYPASS_PATHS` as defense in depth.
    """

    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    entity_type = "policies"

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    @swagger_auto_schema(tags=_OPA_TAG)
    def list(self, request):
        rules = PolicyRule.objects.all()
        data = PolicyRuleSerializer(rules, many=True, context={"request": request}).data
        return Response(data)

    @swagger_auto_schema(tags=_OPA_TAG)
    def create(self, request):
        ser = PolicyRuleSerializer(data=request.data, context={"request": request})
        ser.is_valid(raise_exception=True)
        rule = ser.save()
        try:
            opa_client.push_policy(rule.policy_id, rule.rego_source)
        except Exception as e:
            rule.delete()
            logger.exception("Failed to push new policy to OPA; rolled back Mongo insert")
            return Response(
                {"error": "Failed to push policy to OPA.", "detail": str(e)},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return Response(
            PolicyRuleSerializer(rule, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @swagger_auto_schema(tags=_OPA_TAG)
    def retrieve(self, request, pk=None):
        rule = self._get_or_404(pk)
        return Response(PolicyRuleSerializer(rule, context={"request": request}).data)

    @swagger_auto_schema(tags=_OPA_TAG)
    def update(self, request, pk=None):
        rule = self._get_or_404(pk)
        ser = PolicyRuleSerializer(rule, data=request.data, context={"request": request})
        ser.is_valid(raise_exception=True)
        rule = ser.save()
        opa_client.push_policy(rule.policy_id, rule.rego_source)
        return Response(PolicyRuleSerializer(rule, context={"request": request}).data)

    @swagger_auto_schema(tags=_OPA_TAG)
    def partial_update(self, request, pk=None):
        rule = self._get_or_404(pk)
        ser = PolicyRuleSerializer(
            rule, data=request.data, partial=True, context={"request": request}
        )
        ser.is_valid(raise_exception=True)
        rule = ser.save()
        opa_client.push_policy(rule.policy_id, rule.rego_source)
        return Response(PolicyRuleSerializer(rule, context={"request": request}).data)

    @swagger_auto_schema(tags=_OPA_TAG)
    def destroy(self, request, pk=None):
        rule = self._get_or_404(pk)
        try:
            opa_client.delete_policy(rule.policy_id)
        except Exception as e:
            logger.warning("Failed to delete policy from OPA; deleting Mongo record anyway",
                           extra={"policy_id": rule.policy_id, "error": str(e)})
        rule.delete()
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
        """Dry-run: translate a candidate rule + evaluate against provided input.

        Does NOT persist to Mongo. Pushes a temporary policy to OPA under
        `__dry_run__`, queries, then cleans up.
        """
        rule_data = request.data.get("rule") or {}
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

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _get_or_404(self, pk):
        rule = PolicyRule.objects.filter(policy_id=pk).first()
        if not rule:
            raise NotFound(f"Policy '{pk}' not found.")
        return rule


class UserRoleUpdateView(APIView):
    """PATCH /api/users/<id>/role/ — admin-only role update.

    Enforcement: the `/api/users/` path is in OPA_BYPASS_PATHS at the path
    level, so OPAPermission short-circuits. We therefore enforce admin-only
    access manually here (request.user.role == "admin").
    """

    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    entity_type = "users"
    http_method_names = ["patch", "options"]

    @swagger_auto_schema(tags=_OPA_TAG)
    def patch(self, request, pk=None):
        if getattr(request.user, "role", None) != "admin":
            return Response(
                {"detail": "You do not have permission to perform this action."},
                status=status.HTTP_403_FORBIDDEN,
            )

        new_role = request.data.get("role")
        if new_role not in User.ROLE_CHOICES:
            raise ValidationError({"role": f"Must be one of {User.ROLE_CHOICES}."})

        user = User.objects(id=pk).first()
        if not user:
            raise NotFound(f"User '{pk}' not found.")

        user.role = new_role
        user.save()
        return Response({
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "role": user.role,
        })
