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
    2. Call this import endpoint for each entity type
    3. Terraform state files now contain all existing resources
    4. You can now use normal create/restore/delete APIs
    """

    collection_name_param = openapi.Parameter(
        name="collection_name",
        in_=openapi.IN_QUERY,
        description="Entity type to import (e.g., 'okta_app_oauth', 'okta_user', 'okta_group')",
        type=openapi.TYPE_STRING,
        required=True,
    )

    @swagger_auto_schema(
        manual_parameters=[collection_name_param],
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
                description="Bad request - missing parameters"
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
            entity_name = request.query_params.get("collection_name")

            if not entity_name:
                return Response(
                    {"error": "collection_name query parameter is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            logger.info("=" * 80)
            logger.info(f"IMPORT REQUEST: {entity_name}")
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

            # Call OkTfModules import API
            terraform_server_url = settings.SERVER_URL
            import_url = f"{terraform_server_url}/api/import/"

            logger.info(f"Calling OkTfModules import API: {import_url}")
            logger.info(f"Entity: {entity_name}")

            # Prepare request
            params = {"collection_name": entity_name}
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }

            # Make request to OkTfModules
            response = requests.post(
                import_url,
                params=params,
                headers=headers,
                timeout=300  # 5 minutes timeout for import operations
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
