"""
Cross-tenant entity migration — super-admin only.

POST /api/cross-tenant-migrate/?target_tenant_id=<uuid>

Reads entity records from Tenant A's MongoDB snapshot, strips Okta-issued IDs,
obtains Tenant B's Okta token via M2M (Client Credentials), and creates the
records in Tenant B's Okta org through the existing Terraform pipeline.
No user login to Tenant B is required.
"""
import copy
import logging

import requests
from django.conf import settings
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.authentication import CustomJWTAuthentication
from core.tasks.bulk_tasks import MockRequest
from core.utils.db_utils import get_collection_name
from core.utils.mapping_provider import get_entity_id_mapping, get_nested_field_collections
from core.utils.migration_utils import strip_entity_ids
from core.utils.module_mapping import get_terraform_api_for_entity
from core.utils.okta_helpers import get_okta_headers
from core.utils.restore_utils import (
    fetch_and_merge_restored_data,
    remove_metadata_fields,
    store_created_data,
    update_created_records_with_ids,
)
from core.utils import mapping_handlers
from entities.services.resouce_data_service import EntityDataService

logger = logging.getLogger(__name__)

_METADATA_FIELDS = [
    "operation_type", "created_at", "updated_at",
    "restored_by", "restored_at", "restored_from",
    "unique_id", "_id", "deleted_by", "deleted_at",
    "deleted_from", "cascade_parent_id",
]


def _is_super_admin(request) -> bool:
    user = getattr(request, "user", None)
    if not user:
        return False
    return "super_admin" in (getattr(user, "roles", None) or [])


class CrossTenantMigrateView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # ── Step 1: Auth guard ────────────────────────────────────────────────
        if not _is_super_admin(request):
            return Response(
                {"error": "Only super admins can perform cross-tenant migration."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # ── Step 2: Parse + validate inputs ──────────────────────────────────
        source_tenant_id = request.data.get("source_tenant_id")
        source_db        = request.data.get("source_db")
        target_db        = request.data.get("target_db")
        entity_name      = request.data.get("entity_name")
        record_ids       = request.data.get("record_ids") or []
        target_tenant_id = request.query_params.get("target_tenant_id")

        missing = [
            name for name, val in [
                ("source_tenant_id", source_tenant_id),
                ("source_db",        source_db),
                ("target_db",        target_db),
                ("entity_name",      entity_name),
            ] if not val
        ]
        if missing:
            return Response(
                {"error": f"Missing required body fields: {', '.join(missing)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not target_tenant_id:
            return Response(
                {"error": "Missing required query parameter: target_tenant_id"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Step 3: Resolve both tenants from Supabase ───────────────────────
        from core.utils.tenant_utils import get_tenant_by_id, get_mongo_client_for_tenant

        source_tenant = get_tenant_by_id(source_tenant_id)
        if not source_tenant:
            return Response(
                {"error": f"Source tenant '{source_tenant_id}' not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        target_tenant = get_tenant_by_id(target_tenant_id)
        if not target_tenant:
            return Response(
                {"error": f"Target tenant '{target_tenant_id}' not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not source_db.startswith(source_tenant.mongo_db_prefix + "_"):
            return Response(
                {"error": "Access denied: source_db does not belong to the source tenant."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if not target_db.startswith(target_tenant.mongo_db_prefix + "_"):
            return Response(
                {"error": "Access denied: target_db does not belong to the target tenant."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # ── Step 4: Entity metadata ───────────────────────────────────────────
        collection_name = get_collection_name(entity_name)
        if not collection_name:
            return Response(
                {"error": f"Entity '{entity_name}' not found in resource map."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        id_field = get_entity_id_mapping().get(entity_name)
        if not id_field:
            return Response(
                {"error": f"Entity '{entity_name}' has no ID field configured."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            # ── Step 5: Read records from Tenant A's MongoDB ──────────────────
            source_mongo_client = get_mongo_client_for_tenant(source_tenant)
            service = EntityDataService(
                mongo_client=source_mongo_client,
                db_prefix=source_tenant.mongo_db_prefix,
            )
            iso_date_src = source_db.split("_", 1)[1].split("T")[0]
            records = service.fetch(iso_date_src, entity_name, db_name=source_db)

            if record_ids:
                str_ids = [str(i) for i in record_ids]
                records = [r for r in records if str(r.get(id_field, "")) in str_ids]

            if not records:
                return Response(
                    {"error": "No matching records found in the source snapshot."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            logger.info(
                f"cross_tenant_migrate: found {len(records)} records for '{entity_name}' "
                f"in {source_db} — stripping IDs before migration."
            )

            # ── Step 6: Strip Okta IDs ────────────────────────────────────────
            stripped_records, warnings = strip_entity_ids(entity_name, records)

            # ── Step 7: Get Tenant B's Okta token (M2M, no user login) ───────
            from core.utils.tenant_service_token import get_service_access_token_for_tenant
            access_token, granted_scopes = get_service_access_token_for_tenant(target_tenant)

            # ── Step 8: Connect to Tenant B's MongoDB ─────────────────────────
            target_mongo_client = get_mongo_client_for_tenant(target_tenant)
            target_db_conn = target_mongo_client[target_db]

            # ── Step 9: Store stripped records in Tenant B's _collection ──────
            store_created_data(
                target_db_conn,
                entity_name,
                collection_name,
                copy.deepcopy(stripped_records),
            )
            logger.info(
                f"cross_tenant_migrate: stored {len(stripped_records)} records "
                f"in {target_db}[_{collection_name}] with operation_type='created'."
            )

            # ── Step 10: Build MockRequest for Tenant B ───────────────────────
            mock_request = MockRequest(
                okta_access_token=access_token,
                okta_granted_scopes=granted_scopes,
            )
            mock_request._tenant       = target_tenant
            mock_request._tenant_id    = str(target_tenant.id)
            mock_request._mongo_uri    = target_tenant.mongo_uri
            mock_request._db_prefix    = target_tenant.mongo_db_prefix
            mock_request._mongo_client = target_mongo_client

            # ── Step 11: Terraform merge + call ───────────────────────────────
            tf_response, tf_data = self._run_terraform_create(
                mock_request=mock_request,
                target_mongo_client=target_mongo_client,
                target_db_conn=target_db_conn,
                target_db=target_db,
                entity_name=entity_name,
                collection_name=collection_name,
                id_field=id_field,
                target_tenant=target_tenant,
            )

            if not tf_response.ok:
                logger.error(
                    f"cross_tenant_migrate: Terraform failed "
                    f"(status={tf_response.status_code}): {tf_data}"
                )
                return Response(
                    {"error": "Terraform apply failed.", "details": tf_data},
                    status=status.HTTP_502_BAD_GATEWAY,
                )

            # ── Step 12: Write real Okta IDs back to _collection ─────────────
            created_resources = tf_data.get("created_resources", [])
            if created_resources:
                label_field = mapping_handlers.MAPPED_ENTITIES_HELPERS[
                    "entity_unique_fields"
                ].get(collection_name, "label")
                label_to_id = {r["label"]: r["id"] for r in created_resources}
                update_created_records_with_ids(
                    target_db_conn, collection_name, id_field, label_field, label_to_id
                )
                logger.info(
                    f"cross_tenant_migrate: wrote back {len(created_resources)} "
                    f"real Okta IDs to {target_db}[_{collection_name}]."
                )

            # ── Step 13: Return ───────────────────────────────────────────────
            return Response(
                {
                    "entity_name":    entity_name,
                    "migrated_count": len(stripped_records),
                    "tf_message":     tf_data.get("message", ""),
                    "warnings":       warnings,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as exc:
            logger.exception(f"cross_tenant_migrate: unexpected error — {exc}")
            return Response(
                {"error": "Migration failed due to an internal error.", "details": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # ── Private helper ────────────────────────────────────────────────────────

    def _run_terraform_create(
        self,
        mock_request,
        target_mongo_client,
        target_db_conn,
        target_db,
        entity_name,
        collection_name,
        id_field,
        target_tenant,
    ):
        """
        Replicates the create path from bulk_view.py:1083–1322.

        1. Fetch ALL existing records from Tenant B's target_db (current baseline).
        2. Merge with newly stored created records from _collection.
        3. Strip metadata fields.
        4. POST the complete desired state to OkTf with Tenant B's token.
        """
        active_server_url = (
            getattr(target_tenant, "terraform_server_url", None) or settings.SERVER_URL
        )
        db_prefix = target_tenant.mongo_db_prefix

        # a) Fetch existing records from Tenant B's snapshot (the baseline)
        service = EntityDataService(
            mongo_client=target_mongo_client,
            db_prefix=db_prefix,
        )
        iso_date = target_db.split("_", 1)[1].split("T")[0]
        original_data = service.fetch(iso_date, entity_name, db_name=target_db)
        logger.info(
            f"_run_terraform_create: {len(original_data)} existing records "
            f"in target DB {target_db}."
        )

        # b) Merge original + restored/created records from _collection
        merged_data = fetch_and_merge_restored_data(
            target_db_conn, entity_name, collection_name, id_field, original_data
        )

        # c) Add newly created records that are not yet in merged_data
        #    (records without a real ID are not picked up by merge_restored_with_original)
        restored_collection = target_db_conn[f"_{collection_name}"]
        created_records_from_db = list(
            restored_collection.find({"operation_type": "created"}, {"_id": 0})
        )
        if created_records_from_db:
            merged_ids = {str(r.get(id_field)) for r in merged_data if r.get(id_field)}
            nested_mapping = get_nested_field_collections().get(entity_name)
            records_to_add = []

            for created_record in created_records_from_db:
                rec_id = created_record.get(id_field)
                if rec_id and str(rec_id) in merged_ids:
                    continue

                if nested_mapping:
                    unique_id = created_record.get("unique_id")
                    if unique_id:
                        for nested_field, nested_coll_name in nested_mapping.items():
                            nested_coll = f"_{nested_coll_name}"
                            if nested_coll in target_db_conn.list_collection_names():
                                nested_data = list(
                                    target_db_conn[nested_coll].find(
                                        {
                                            "unique_id": unique_id,
                                            "operation_type": {"$ne": "deleted"},
                                        },
                                        {"_id": 0},
                                    )
                                )
                                created_record[nested_field] = nested_data
                            else:
                                created_record[nested_field] = []

                records_to_add.append(created_record)

            merged_data.extend(records_to_add)
            logger.info(
                f"_run_terraform_create: added {len(records_to_add)} new created records, "
                f"total = {len(merged_data)}."
            )

        # d) Remove metadata fields before sending to Terraform
        remove_metadata_fields(merged_data)
        for record in merged_data:
            for val in record.values():
                if isinstance(val, list):
                    for item in val:
                        if isinstance(item, dict):
                            for field in _METADATA_FIELDS:
                                item.pop(field, None)

        logger.info(
            f"_run_terraform_create: sending {len(merged_data)} records to Terraform."
        )

        # e) Resolve Terraform endpoint
        terraform_api = get_terraform_api_for_entity(entity_name)
        if not terraform_api:
            raise ValueError(f"No Terraform API configured for entity: {entity_name}")
        terraform_url = f"{active_server_url}{terraform_api}"

        # f) Derive Okta org fields from Tenant B's domain
        okta_org_name = None
        okta_base_url = None
        if getattr(target_tenant, "okta_domain", None):
            domain_clean = (
                target_tenant.okta_domain
                .replace("https://", "")
                .replace("http://", "")
                .rstrip("/")
            )
            parts = domain_clean.split(".", 1)
            okta_org_name = parts[0]
            okta_base_url = parts[1] if len(parts) > 1 else "okta.com"

        # g) POST to OkTf with Tenant B's service token
        tf_headers = get_okta_headers(mock_request)
        tf_response = requests.post(
            terraform_url,
            params={"collection_name": collection_name},
            json={
                "data":          merged_data,
                "tenant_id":     str(target_tenant.id),
                "okta_org_name": okta_org_name,
                "okta_base_url": okta_base_url,
                "bucket_name":   getattr(target_tenant, "supabase_bucket_name", None),
                "supabase_url":  getattr(target_tenant, "supabase_url", None),
                "supabase_key":  getattr(target_tenant, "supabase_key", None),
            },
            headers=tf_headers,
        )

        try:
            tf_data = tf_response.json()
        except Exception:
            tf_data = {"message": tf_response.text}

        return tf_response, tf_data
