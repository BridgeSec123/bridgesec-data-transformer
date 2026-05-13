"""
Confirm-delete endpoint — Phase 2 of the Plan → Confirm/Deny → Apply delete flow.

After the user reviews the terraform plan returned by
  POST /restore/<db>/<entity>/?operation_type=delete&phase=plan
they confirm or deny here:
  POST /confirm-delete/?plan_id=<id>&action=confirm   → execute deletion
  POST /confirm-delete/?plan_id=<id>&action=deny      → reject and clean up plan

This view loads the stored plan, validates it, then either calls OkTf to execute
the full cascade destroy (action=confirm) or removes the plan without touching
Okta (action=deny).
"""
import logging

import requests
from core.authentication import CustomJWTAuthentication
from core.utils.jwt_utils import get_user_from_request
from core.utils.mongo_utils import ensure_mongo_connection
from core.utils.okta_helpers import get_okta_headers
from core.utils.tenant_utils import get_tenant_from_request, get_mongo_client_for_tenant
from core.utils.restore_utils import (
    load_deletion_plan,
    mark_plan_applied,
    update_deletion_status,
    remove_deletion_plan_records,
    cancel_deletion_plan,
)
from core.utils.verification import verify_deletion_complete
from django.conf import settings
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from core.permissions.opa_permission import OPAPermission

logger = logging.getLogger(__name__)

mongo_client = settings.MONGO_CLIENT


class ConfirmDeletionView(APIView):
    """
    Confirm or deny a pending deletion plan.

    POST /confirm-delete/?plan_id=<id>&action=confirm
        Executes the deletion via Terraform (apply phase).

    POST /confirm-delete/?plan_id=<id>&action=deny
        Rejects the deletion — removes the plan and staged records from MongoDB.
        No changes are made to Okta.

    The plan must have been created via
      POST /restore/<db>/<entity>/?operation_type=delete
    within the last 15 minutes and by the same user making this request.
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated, OPAPermission]

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                name="plan_id",
                in_=openapi.IN_QUERY,
                description="UUID of the pending deletion plan (compulsory)",
                type=openapi.TYPE_STRING,
                required=True,
            ),
            openapi.Parameter(
                name="action",
                in_=openapi.IN_QUERY,
                description="'confirm' to execute deletion, 'deny' to reject and clean up the plan",
                type=openapi.TYPE_STRING,
                required=True,
                enum=["confirm", "deny"],
            ),
        ]
    )
    def post(self, request):
        from core.utils.tenant_utils import is_super_admin
        if is_super_admin(request.user):
            return Response(
                {"error": "Super admin cannot perform delete operations."},
                status=status.HTTP_403_FORBIDDEN,
            )

        plan_id = request.query_params.get("plan_id")
        action = request.query_params.get("action")

        if not plan_id:
            return Response(
                {"error": "plan_id query param is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if action not in ("confirm", "deny"):
            return Response(
                {"error": "action query param is required and must be 'confirm' or 'deny'"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if action == "deny":
            return self._handle_denial(request, plan_id)

        # --- action == "confirm" ---
        requesting_user = get_user_from_request(request)
        tenant = get_tenant_from_request(request)
        active_mongo_client = get_mongo_client_for_tenant(tenant) if tenant else mongo_client
        tenant_mongo_uri = tenant.mongo_uri if tenant else None

        plans_col = mongo_client[settings.MONGO_DB_NAME]["pending_deletion_plans"]

        # Load and validate the plan
        plan, err = load_deletion_plan(plan_id, requesting_user, plans_col)
        if err:
            http_status = err.pop("status")
            return Response(err, status=http_status)

        # Unpack stored plan metadata
        db_name = plan["db_name"]
        entity_name = plan["entity_name"]
        collection_name = plan["collection_name"]
        id_field = plan["id_field"]
        modified_data = plan["merged_data"]
        terraform_params = plan["terraform_params"]   # No phase=plan
        terraform_url = plan["terraform_url"]
        cascade_info = plan.get("cascade_info", {})

        ensure_mongo_connection(db_name, mongo_uri=tenant_mongo_uri)
        current_db = active_mongo_client[db_name]

        # Load the actual deleted records from _<collection_name> using plan_id tag.
        # These were stored there during phase=plan — no duplication in pending_deletion_plans.
        complete_deleted_records = list(
            current_db[f"_{collection_name}"].find(
                {"plan_id": plan_id, "operation_type": "deletion_pending"},
                {"_id": 0},
            )
        )
        if not complete_deleted_records:
            return Response(
                {
                    "error": "plan_records_missing",
                    "message": f"No pending records found for plan '{plan_id}' in _{collection_name}.",
                    "plan_id": plan_id,
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        parent_ids = [
            doc.get(id_field)
            for doc in complete_deleted_records
            if doc.get(id_field)
        ]

        # Mark plan as applied BEFORE the OkTf call to prevent double-submit races.
        # If OkTf fails, the plan stays "applied" but records will show deletion_failed.
        mark_plan_applied(plan_id, plans_col)

        # Call OkTf — full cascade destroy (-auto-approve runs inside OkTf)
        tf_headers = get_okta_headers(request)
        logger.info(
            f"Confirm delete: calling OkTf apply for plan {plan_id} "
            f"({len(parent_ids)} parent(s), entity={entity_name})",
            extra={"operation": "Confirm Deletion"},
        )

        tf_response = requests.post(
            terraform_url,
            params=terraform_params,
            json={"data": modified_data},
            headers=tf_headers,
        )

        try:
            tf_data = tf_response.json()
        except Exception:
            tf_data = {"message": "Unknown response from Terraform"}

        tf_message = tf_data.get("message", "No message returned")

        if 200 <= tf_response.status_code < 300:
            # SUCCESS — update deletion_pending → deleted so records are preserved in MongoDB
            # with full audit metadata (deleted_by, deleted_from, deleted_at, plan_id).
            update_deletion_status(
                current_db, entity_name, collection_name,
                parent_ids, new_status="deleted"
            )

            # Update cascade nested records as well
            if cascade_info and "nested_deletions" in cascade_info:
                for _, nested_info in cascade_info["nested_deletions"].items():
                    update_deletion_status(
                        current_db, entity_name,
                        nested_info["collection"],
                        nested_info["ids"],
                        new_status="deleted"
                    )

            logger.info(
                f"Confirm delete: successfully deleted {len(parent_ids)} parent(s) "
                f"and cascade records for entity={entity_name}",
                extra={"operation": "Confirm Deletion"},
            )

            # Run deletion verification
            okta_access_token = None
            if hasattr(request, "session"):
                okta_access_token = request.session.get("okta_access_token")

            verification_results = []
            for doc in complete_deleted_records:
                try:
                    verification = verify_deletion_complete(
                        entity_type=entity_name,
                        entity_record=doc,
                        deletion_results=tf_data,
                        access_token=okta_access_token,
                    )
                    verification_results.append(verification)
                except Exception as exc:
                    logger.error(f"Verification failed for record: {exc}")
                    verification_results.append({
                        "verified": False,
                        "error": str(exc),
                        "entity_record": doc,
                    })

            verified_count = sum(1 for v in verification_results if v.get("verified"))
            failed_count = len(verification_results) - verified_count

            response_data = {
                "tf_message": tf_message,
                "message": f"Operations completed: {len(parent_ids)} deleted",
                "plan_id": plan_id,
                "restored_db": db_name,
                "collection": f"_{collection_name}",
                "record_count": len(modified_data),
                "operations": {"deleted": len(parent_ids), "restored": 0, "created": 0},
            }

            if cascade_info:
                response_data["cascade_info"] = cascade_info

            response_data["verification"] = {
                "performed": True,
                "total_verified": verified_count,
                "total_failed": failed_count,
                "results": verification_results,
            }

            if failed_count > 0:
                response_data["warning"] = (
                    "Deletion completed but verification found issues. "
                    "Check 'verification' field for details."
                )

            return Response(response_data, status=status.HTTP_200_OK)

        else:
            # FAILURE — mark records as deletion_failed
            logger.error(
                f"Confirm delete: OkTf apply failed (status {tf_response.status_code}) "
                f"for plan {plan_id}",
                extra={"operation": "Confirm Deletion"},
            )

            update_deletion_status(
                current_db, entity_name, collection_name,
                parent_ids, new_status="deletion_failed",
                terraform_error=tf_message,
            )

            if cascade_info and "nested_deletions" in cascade_info:
                for _, nested_info in cascade_info["nested_deletions"].items():
                    update_deletion_status(
                        current_db, entity_name,
                        nested_info["collection"],
                        nested_info["ids"],
                        new_status="deletion_failed",
                        terraform_error=tf_message,
                    )

            return Response({
                "error": "Terraform deletion failed",
                "tf_message": tf_message,
                "tf_status_code": tf_response.status_code,
                "plan_id": plan_id,
                "message": (
                    "Deletion marked as failed. Records remain in 'deletion_failed' state "
                    "in MongoDB for manual review."
                ),
                "failed_ids": parent_ids,
                "cascade_info": cascade_info,
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _handle_denial(self, request, plan_id):
        """
        Deny a pending deletion plan.

        Validates the plan (existence, expiry, ownership), removes all staged
        deletion_pending records from the snapshot DB, and deletes the plan
        document. No changes are made to Okta.
        """
        requesting_user = get_user_from_request(request)
        tenant = get_tenant_from_request(request)
        active_mongo_client = get_mongo_client_for_tenant(tenant) if tenant else mongo_client
        tenant_mongo_uri = tenant.mongo_uri if tenant else None

        plans_col = mongo_client[settings.MONGO_DB_NAME]["pending_deletion_plans"]

        plan, err = load_deletion_plan(plan_id, requesting_user, plans_col)
        if err:
            http_status = err.pop("status")
            return Response(err, status=http_status)

        db_name = plan["db_name"]
        collection_name = plan["collection_name"]
        cascade_info = plan.get("cascade_info", {})

        ensure_mongo_connection(db_name, mongo_uri=tenant_mongo_uri)
        current_db = active_mongo_client[db_name]

        # Clean up all deletion_pending records staged during the plan phase
        remove_deletion_plan_records(current_db, collection_name, plan_id, cascade_info)

        # Remove the plan document from pending_deletion_plans
        cancel_deletion_plan(plan_id, plans_col)

        logger.info(
            f"Deletion plan {plan_id} denied by {requesting_user}",
            extra={"operation": "Deny Deletion"},
        )

        return Response(
            {
                "message": "Deletion denied. The pending plan has been removed and no changes were made to Okta.",
                "plan_id": plan_id,
                "denied_by": requesting_user,
            },
            status=status.HTTP_200_OK,
        )
