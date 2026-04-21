import logging

from entities.views.base_view import BaseEntityViewSet
from entities.okta_entities.domain.domain_models import Domain
from entities.okta_entities.domain.domain_serializers import DomainSerializer

logger = logging.getLogger(__name__)


class DomainViewSet(BaseEntityViewSet):
    okta_endpoint = "/api/v1/domains"
    entity_type = "domains"
    serializer_class = DomainSerializer
    model = Domain

    def extract_data(self, okta_data):
        if isinstance(okta_data, dict):
            items = okta_data.get("domains", okta_data.get("value", [okta_data]))
        elif isinstance(okta_data, list):
            items = okta_data
        else:
            items = []

        formatted_data = []
        for item in items:
            if not isinstance(item, dict):
                logger.warning("Skipping invalid record (not a dict): %s", item)
                continue

            raw_dns = item.get("dnsRecords", [])
            dns_records = [
                {
                    "expiration": r.get("expiration", ""),
                    "fqdn": r.get("fqdn", ""),
                    "record_type": r.get("recordType", ""),
                    "values": r.get("values", []),
                }
                for r in (raw_dns if isinstance(raw_dns, list) else [])
                if isinstance(r, dict)
            ]

            formatted_data.append({
                "domain_id": item.get("id", ""),
                "name": item.get("domain", item.get("name", "")),
                "brand_id": item.get("brandId", ""),
                "certificate_source_type": item.get("certificateSourceType", ""),
                "validation_status": item.get("validationStatus", ""),
                "dns_records": dns_records,
                "public_certificate": item.get("publicCertificate", {}),
            })

        logger.info("Extracted %d Domain records", len(formatted_data))
        return formatted_data

    def fetch_and_store_data(self, db_name, request=None):
        try:
            okta_response, status_code, _ = self.fetch_from_okta(request=request)
            if status_code == 200:
                extracted_data = self.extract_data(okta_response)
                self.store_data(extracted_data, db_name=db_name)
                return {"domains": extracted_data}
            return {"domains": []}
        except Exception as e:
            logger.exception("Error in DomainViewSet.fetch_and_store_data: %s", str(e))
            return {"domains": []}
