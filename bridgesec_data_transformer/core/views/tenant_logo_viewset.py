"""
Tenant logo management API.

GET    /api/tenants/<id>/logo/   Return permanent public URL for the tenant's logo.
POST   /api/tenants/<id>/logo/   Upload / replace the tenant's logo (multipart field: "logo").
DELETE /api/tenants/<id>/logo/   Remove the tenant's logo.

Storage: public Supabase bucket "tenant-logos" (create it manually in Supabase dashboard).
URL is permanent — no signed tokens, no expiry. Stored directly on the tenant row.
"""
import logging
import mimetypes

from django.conf import settings
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.authentication import CustomJWTAuthentication
from core.utils.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

LOGO_BUCKET = "tenant-logos"
ALLOWED_MIME_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp", "image/svg+xml"}
MAX_FILE_BYTES = 2 * 1024 * 1024  # 2 MB

# mimetypes can return non-standard extensions; normalise the common cases
_EXT_NORMALISE = {".jpe": ".jpg", ".jpeg": ".jpg"}


def _can_access_tenant(request, tenant_id: str) -> bool:
    user_roles = getattr(request.user, "roles", None) or []
    if "super_admin" in user_roles:
        return True
    return str(getattr(request, "_tenant_id", None)) == str(tenant_id)


def _can_manage_logo(request, tenant_id: str) -> bool:
    user_roles = getattr(request.user, "roles", None) or []
    if "super_admin" in user_roles:
        return True
    if "admin" in user_roles and str(getattr(request, "_tenant_id", None)) == str(tenant_id):
        return True
    return False


class TenantLogoView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, tenant_id):
        if not _can_access_tenant(request, tenant_id):
            return Response({"error": "Access denied"}, status=status.HTTP_403_FORBIDDEN)

        from core.utils.supabase_tenant import SupabaseTenant
        tenant = SupabaseTenant.get_by_id(str(tenant_id))
        if not tenant:
            return Response({"error": "Tenant not found"}, status=status.HTTP_404_NOT_FOUND)

        return Response({"logo_url": getattr(tenant, "logo_url", None)}, status=status.HTTP_200_OK)

    def post(self, request, tenant_id):
        if not _can_manage_logo(request, tenant_id):
            return Response({"error": "Admin access required"}, status=status.HTTP_403_FORBIDDEN)

        from core.utils.supabase_tenant import SupabaseTenant
        tenant = SupabaseTenant.get_by_id(str(tenant_id))
        if not tenant:
            return Response({"error": "Tenant not found"}, status=status.HTTP_404_NOT_FOUND)

        file_obj = request.FILES.get("logo")
        if not file_obj:
            return Response(
                {"error": "No file provided. Send the image as multipart field 'logo'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        content_type = (file_obj.content_type or "").split(";")[0].strip()
        if content_type not in ALLOWED_MIME_TYPES:
            return Response(
                {"error": f"Unsupported type '{content_type}'. Allowed: {sorted(ALLOWED_MIME_TYPES)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if file_obj.size > MAX_FILE_BYTES:
            return Response(
                {"error": f"File too large ({file_obj.size:,} bytes). Max: {MAX_FILE_BYTES:,} bytes."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ext = mimetypes.guess_extension(content_type) or ""
        ext = _EXT_NORMALISE.get(ext, ext)
        logo_path = f"{tenant_id}/logo{ext}"

        try:
            client = get_supabase_client()
            client.storage.from_(LOGO_BUCKET).upload(
                logo_path,
                file_obj.read(),
                file_options={"content-type": content_type, "upsert": "true"},
            )
            public_url = client.storage.from_(LOGO_BUCKET).get_public_url(logo_path)
            SupabaseTenant.update(str(tenant_id), {
                "logo_bucket_path": logo_path,
                "logo_url": public_url,
            })
            logger.info(
                "Logo uploaded for tenant '%s' at '%s' by %s",
                tenant_id, logo_path, getattr(request.user, "email", "unknown"),
            )
            return Response({"logo_url": public_url}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error("TenantLogoView.post(%s) failed: %s", tenant_id, e, exc_info=True)
            return Response({"error": "Failed to upload logo"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, tenant_id):
        if not _can_manage_logo(request, tenant_id):
            return Response({"error": "Admin access required"}, status=status.HTTP_403_FORBIDDEN)

        from core.utils.supabase_tenant import SupabaseTenant
        tenant = SupabaseTenant.get_by_id(str(tenant_id))
        if not tenant:
            return Response({"error": "Tenant not found"}, status=status.HTTP_404_NOT_FOUND)

        logo_path = getattr(tenant, "logo_bucket_path", None)
        if not logo_path:
            return Response({"message": "No logo configured"}, status=status.HTTP_200_OK)

        try:
            get_supabase_client().storage.from_(LOGO_BUCKET).remove([logo_path])
            SupabaseTenant.update(str(tenant_id), {"logo_bucket_path": None, "logo_url": None})
            logger.info(
                "Logo removed for tenant '%s' by %s",
                tenant_id, getattr(request.user, "email", "unknown"),
            )
            return Response({"message": "Logo removed"}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error("TenantLogoView.delete(%s) failed: %s", tenant_id, e, exc_info=True)
            return Response({"error": "Failed to remove logo"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
