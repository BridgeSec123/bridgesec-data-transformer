"""
Entity configuration API — per-tenant backup entity enable/disable.

GET  /api/entity-config/                                          → all entities + enabled status
PUT  /api/entity-config/                                          → batch update (entity + collection)
PATCH /api/entity-config/<config_name>/                           → toggle single entity
PATCH /api/entity-config/<entity_name>/collections/<col_name>/   → toggle single collection

Permission:
- Read  → any authenticated user
- Write → super_admin, tenant_admin, entity_config_admin

URL param is <config_name> (not <entity_name>) to avoid OPAPermission
resolving the wrong entity from the URL kwarg.
"""
import logging

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import BasePermission, SAFE_METHODS
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.entity_config import (
    get_entity_catalog_with_status,
    bulk_update_entity_config,
    toggle_collection_config,
)
from core.utils.jwt_utils import get_user_from_request
from core.utils.tenant_utils import get_tenant_from_request

logger = logging.getLogger(__name__)

_WRITE_ROLES = {"super_admin", "tenant_admin", "entity_config_admin"}


class EntityConfigPermission(BasePermission):
    """
    Read: any authenticated user.
    Write: super_admin, tenant_admin or entity_config_admin only.
    Intentionally does NOT go through OPA — simple inline role check.
    """

    def has_permission(self, request, view):
        if not getattr(request.user, "is_authenticated", False):
            return False
        if request.method in SAFE_METHODS:
            return True
        roles = set(getattr(request.user, "roles", []) or [])
        return bool(roles & _WRITE_ROLES)


def _resolve_tenant_id(request):
    """
    Resolve the tenant_id to use for this request.
    - super_admin + ?tenant_id= → use that tenant
    - super_admin without ?tenant_id= → global (None) config
    - Everyone else → their own tenant
    - MULTI_TENANCY_ENABLED=False → always None
    """
    if not getattr(settings, "MULTI_TENANCY_ENABLED", False):
        return None

    roles = set(getattr(request.user, "roles", []) or [])
    if "super_admin" in roles:
        tid = request.query_params.get("tenant_id")
        return tid if tid else None

    tenant = get_tenant_from_request(request)
    return str(tenant.id) if tenant else None


class EntityConfigListView(APIView):
    permission_classes = [EntityConfigPermission]

    def get(self, request):
        """
        Return all entities with their enabled status for the caller's tenant.
        Groups by category in the response. Each collection now carries
        is_active and enabled fields.
        """
        tenant_id = _resolve_tenant_id(request)
        catalog = get_entity_catalog_with_status(tenant_id)

        # Group by category for easier frontend consumption
        grouped = {}
        for item in catalog:
            cat = item["category"]
            grouped.setdefault(cat, []).append(item)

        return Response({
            "tenant_id": tenant_id,
            "categories": [
                {"category": cat, "entities": entities}
                for cat, entities in sorted(grouped.items())
            ],
            "total": len(catalog),
        })

    def put(self, request):
        """
        Batch update enabled/disabled for multiple entities and/or collections.

        Body: [
            {"name": "users", "enabled": false},
            {"name": "apps", "collection": "app_oauth", "enabled": false},
            ...
        ]
        Entity-level entries (no "collection" key) behave exactly as before.
        Collection-level entries (with "collection" key) target that collection only.
        """
        updates = request.data
        if not isinstance(updates, list):
            return Response(
                {"detail": "Expected a list of {name, enabled} objects."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        tenant_id = _resolve_tenant_id(request)
        user = get_user_from_request(request)
        updated_by = getattr(user, "email", None) or getattr(user, "username", "")

        result = bulk_update_entity_config(tenant_id, updates, updated_by)

        if result["errors"]:
            return Response(
                {"tenant_id": tenant_id, "updated": result["updated"], "errors": result["errors"]},
                status=status.HTTP_207_MULTI_STATUS,
            )
        return Response({"tenant_id": tenant_id, "updated": result["updated"]}, status=status.HTTP_200_OK)


class EntityConfigDetailView(APIView):
    permission_classes = [EntityConfigPermission]

    def patch(self, request, config_name):
        """
        Toggle a single entity.
        Body: {"enabled": true}
        URL param is config_name (not entity_name) to avoid OPA entity resolution.
        """
        enabled = request.data.get("enabled")
        if enabled is None:
            return Response(
                {"detail": "'enabled' field is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        tenant_id = _resolve_tenant_id(request)
        user = get_user_from_request(request)
        updated_by = getattr(user, "email", None) or getattr(user, "username", "")

        result = bulk_update_entity_config(
            tenant_id,
            [{"name": config_name, "enabled": enabled}],
            updated_by,
        )

        if result["errors"]:
            return Response(
                {"detail": result["errors"][0]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"tenant_id": tenant_id, "name": config_name, "enabled": enabled}, status=status.HTTP_200_OK)


class EntityConfigCollectionView(APIView):
    """PATCH /api/entity-config/<entity_name>/collections/<collection_name>/"""
    permission_classes = [EntityConfigPermission]

    def patch(self, request, entity_name, collection_name):
        """
        Toggle a single collection within an entity.
        Body: {"enabled": true}

        Rules:
        - Enabling a collection requires the parent entity to be enabled first.
        - is_active=False collections cannot be enabled (platform constraint).
        """
        enabled = request.data.get("enabled")
        if enabled is None:
            return Response(
                {"detail": "'enabled' field is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        tenant_id = _resolve_tenant_id(request)

        # Guard: when enabling a collection, parent entity must be enabled
        if enabled:
            catalog = get_entity_catalog_with_status(tenant_id)
            parent = next((e for e in catalog if e["name"] == entity_name), None)
            if parent is None:
                return Response(
                    {"detail": f"Entity '{entity_name}' not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            if not parent["enabled"]:
                return Response(
                    {
                        "detail": (
                            f"Parent entity '{entity_name}' must be enabled "
                            "before enabling individual collections."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            # Find the collection and check is_active
            col = next(
                (c for c in parent.get("collections", []) if c["collection_name"] == collection_name),
                None,
            )
            if col and not col.get("is_active", True):
                return Response(
                    {"detail": f"Collection '{collection_name}' is not active on this platform."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        user = get_user_from_request(request)
        updated_by = getattr(user, "email", None) or getattr(user, "username", "")

        result = toggle_collection_config(
            tenant_id, entity_name, collection_name, bool(enabled), updated_by
        )

        if result["errors"]:
            return Response(
                {"detail": result["errors"][0]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {"tenant_id": tenant_id, "entity_name": entity_name, "collection_name": collection_name, "enabled": enabled},
            status=status.HTTP_200_OK,
        )
