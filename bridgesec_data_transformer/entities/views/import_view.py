"""
Import existing Okta resources into Terraform state files.
"""
import logging
import requests
from django.conf import settings
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions.decorators import require_permission
from core.utils.db_utils import get_collection_name

logger = logging.getLogger(__name__)


class ImportResourcesView(APIView):
    """
    Import existing Okta resources into Terraform state files.

    This endpoint triggers the import of existing Okta resources from MongoDB
    into Terraform state files via the OkTfModules API.

    Use this endpoint to populate state files with existing resources
    BEFORE performing any create/restore/delete operations.

    Workflow:
    1. Run bulk fetch to populate MongoDB with Okta data
    2. Call GET /db-map/ to get available snapshots and pick a db_name
    3. Call this import endpoint with entity_name and db_name
    4. Terraform state files now contain all existing resources
    5. You can now use normal create/restore/delete APIs
    """

    entity_name_param = openapi.Parameter(
        name="entity_name",
        in_=openapi.IN_QUERY,
        description="Mapped entity display name (e.g., 'App Oauth', 'Users', 'Groups')",
        type=openapi.TYPE_STRING,
        required=True,
    )

    db_name_param = openapi.Parameter(
        name="db_name",
        in_=openapi.IN_QUERY,
        description="MongoDB snapshot database name from db-map API (e.g., 'bridgesec_2026-03-10T0357')",
        type=openapi.TYPE_STRING,
        required=True,
    )

    @require_permission("import_resources")
    @swagger_auto_schema(
        manual_parameters=[entity_name_param, db_name_param],
        responses={
            200: openapi.Response(
                description="Import completed successfully",
                examples={
                    "application/json": {
                        "success": True,
                        "message": "Successfully imported 15 okta_app_oauth resources",
                        "imported": [],
                        "failed": [],
                        "skipped": [],
                        "summary": {
                            "total_imported": 15,
                            "total_failed": 0,
                            "total_skipped": 0
                        }
                    }
                }
            ),
            400: openapi.Response(
                description="Bad request - missing or invalid parameters"
            ),
            500: openapi.Response(
                description="Import failed"
            )
        }
    )
    def post(self, request, *args, **kwargs):
        """Import existing resources for a specific entity type into Terraform state"""
        try:
            # Extract parameters
            entity_name = request.query_params.get("entity_name")
            db_name = request.query_params.get("db_name")

            if not entity_name:
                return Response(
                    {"error": "entity_name query parameter is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not db_name:
                return Response(
                    {"error": "db_name query parameter is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Normalize whitespace and resolve display name to collection name
            entity_name = " ".join(entity_name.split())
            collection_name = get_collection_name(entity_name)

            if not collection_name:
                return Response(
                    {"error": f"Unknown entity: '{entity_name}'. Check RESOURCE_COLLECTION_MAP for valid names."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            logger.info("=" * 80)
            logger.info(f"IMPORT REQUEST: {entity_name} -> {collection_name} (db: {db_name})")
            logger.info("=" * 80)

            # Get Okta access token from session
            access_token = request.session.get("okta_access_token")

            if not access_token:
                return Response(
                    {
                        "error": "No Okta access token found in session. Please login first.",
                        "hint": "Use /okta/login/ to authenticate"
                    },
                    status=status.HTTP_401_UNAUTHORIZED
                )

            # Call OkTfModules import API — OkTf is one shared instance for every tenant.
            from core.utils.tenant_utils import get_tenant_from_request
            _tenant = get_tenant_from_request(request)
            import_url = f"{settings.SERVER_URL}/api/import/"

            logger.info(f"Calling OkTfModules import API: {import_url}")
            logger.info(f"Entity: {entity_name} | Collection: {collection_name} | DB: {db_name}")

            # Prepare request
            params = {
                "collection_name": collection_name,
                "db_name": db_name,
            }
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }

            okta_org_name = None
            okta_base_url = None
            if _tenant and _tenant.okta_domain:
                domain_clean = _tenant.okta_domain.replace("https://", "").replace("http://", "").rstrip("/")
                parts = domain_clean.split(".", 1)
                okta_org_name = parts[0]
                okta_base_url = parts[1] if len(parts) > 1 else "okta.com"

            # Make request to OkTfModules
            response = requests.post(
                import_url,
                params=params,
                json={
                    "tenant_id":     str(_tenant.id) if _tenant else None,
                    "okta_org_name": okta_org_name,
                    "okta_base_url": okta_base_url,
                    "bucket_name":   _tenant.supabase_bucket_name if _tenant else None,
                    "supabase_url":  _tenant.supabase_url if _tenant else None,
                    "supabase_key":  _tenant.supabase_key if _tenant else None,
                },
                headers=headers,
                timeout=300
            )

            # Parse response
            try:
                response_data = response.json()
            except Exception:
                response_data = {"error": "Invalid response from Terraform service"}

            # Return response from OkTfModules
            if response.status_code == 200:
                logger.info(f"Import SUCCESS: {response_data.get('message', 'Completed')}")
                logger.info("=" * 80)
                return Response(response_data, status=status.HTTP_200_OK)
            else:
                logger.error(f"Import FAILED: {response_data.get('error', 'Unknown error')}")
                logger.info("=" * 80)
                return Response(
                    response_data,
                    status=response.status_code or status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except requests.RequestException as e:
            logger.exception("Error calling OkTfModules API")
            return Response(
                {
                    "error": "Failed to communicate with Terraform service",
                    "details": str(e)
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as e:
            logger.exception("Exception during import")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
