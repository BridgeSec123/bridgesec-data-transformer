import logging

from entities.views.base_view import BaseEntityViewSet

logger = logging.getLogger(__name__)

class BaseAuthenticatorViewSet(BaseEntityViewSet):
    def fetch_and_store_data(self, db_name, request=None):
        extracted_data = {}

        from entities.registry import AUTHENTICATOR_ENTITY_VIEWSETS

        for entity_name, viewset_class in AUTHENTICATOR_ENTITY_VIEWSETS.items():
            try:
                viewset_instance = viewset_class()
                viewset_instance.request = request
                extracted_data[entity_name] = []

                okta_response, status_code, _ = viewset_instance.fetch_from_okta(request=request)
                if status_code == 200:
                    entity_data = viewset_instance.extract_data(okta_response)
                    extracted_data[entity_name].extend(entity_data)
            except Exception as e:
                logger.exception(f"Error processing {entity_name}: {str(e)}")
                extracted_data[entity_name] = []

        for entity_name, data in extracted_data.items():
            viewset_instance = AUTHENTICATOR_ENTITY_VIEWSETS[entity_name]()
            viewset_instance.request = request
            viewset_instance.store_data(data, db_name)

        return extracted_data
