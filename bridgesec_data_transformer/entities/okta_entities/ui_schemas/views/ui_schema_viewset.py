import logging

from entities.views.base_view import BaseEntityViewSet
from entities.okta_entities.ui_schemas.ui_schema_models import UiSchema
from entities.okta_entities.ui_schemas.ui_schema_serializers import UiSchemaSerializer

logger = logging.getLogger(__name__)


def _normalize_element(element):
    if not isinstance(element, dict):
        return element
    options_raw = element.get("options", {}) or {}
    return {
        "label": element.get("label", ""),
        "scope": element.get("scope", ""),
        "type": element.get("type", ""),
        "options": {"format": options_raw.get("format", "")} if options_raw else {},
    }


def _normalize_ui_schema(raw):
    if not isinstance(raw, dict):
        return {}
    elements = [_normalize_element(e) for e in (raw.get("elements") or [])]
    return {
        "button_label": raw.get("buttonLabel", ""),
        "type": raw.get("type", ""),
        "label": raw.get("label", ""),
        "elements": elements,
    }


class UiSchemaViewSet(BaseEntityViewSet):
    okta_endpoint = "/api/v1/ui-schemas"
    entity_type = "okta_ui_schema"
    serializer_class = UiSchemaSerializer
    model = UiSchema

    def extract_data(self, okta_data):
        items = okta_data if isinstance(okta_data, list) else [okta_data]
        formatted_data = []
        for item in items:
            if not isinstance(item, dict):
                logger.warning("Skipping invalid record (not a dict): %s", item)
                continue
            formatted_data.append({
                "ui_schema_id": item.get("id", ""),
                "created": item.get("created", ""),
                "last_updated": item.get("lastUpdated", ""),
                "ui_schema": _normalize_ui_schema(item.get("uiSchema") or {}),
            })
        logger.info("Extracted %d UI Schema records", len(formatted_data))
        return formatted_data

    def fetch_and_store_data(self, db_name, request=None):
        try:
            okta_response, status_code, _ = self.fetch_from_okta(request=request)
            if status_code == 200:
                extracted_data = self.extract_data(okta_response)
                self.store_data(extracted_data, db_name=db_name)
                return {"ui_schemas": extracted_data}
            return {"ui_schemas": []}
        except Exception as e:
            logger.exception("Error in UiSchemaViewSet.fetch_and_store_data: %s", str(e))
            return {"ui_schemas": []}
