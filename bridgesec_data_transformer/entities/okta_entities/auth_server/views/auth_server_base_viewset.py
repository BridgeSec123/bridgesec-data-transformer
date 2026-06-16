import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from core.utils.entity_mapping import clean_entity_data
from entities.views.base_view import BaseEntityViewSet

logger = logging.getLogger(__name__)


class BaseAuthServerViewSet(BaseEntityViewSet):
    """
    Base ViewSet to handle fetching and storing both Auth Servers and Sub-Entities data dynamically.
    """

    def fetch_and_store_data(self, db_name, request=None):
        logger.info("Starting fetch and store process for auth server and sub-entities.")
        extracted_data = {}

        from entities.registry import AUTH_SERVER_ENTITY_VIEWSETS

        for entity_name, viewset_class in AUTH_SERVER_ENTITY_VIEWSETS.items():
            viewset_instance = viewset_class()
            viewset_instance.request = request

            if entity_name == "auth_servers" or entity_name == "auth_servers_default":
                data, status_code, rate_limit = viewset_instance.fetch_from_okta(request=request)
                extracted_data[entity_name] = viewset_instance.extract_data(data)

            elif entity_name == "auth_server_policy_rules":
                extracted_data[entity_name] = []
                policies = extracted_data.get("auth_server_policy", [])

                def _fetch_policy_rules(policy, _vi=viewset_instance, _req=request):
                    auth_server_id = policy.get("auth_server_id")
                    policy_id = policy.get("policy_id")
                    if not auth_server_id:
                        logger.warning(f"Could not find auth_server_id for {auth_server_id}, skipping policy rules.")
                        return []
                    data = _vi.fetch_from_okta(auth_server_id, policy_id, request=_req)
                    return _vi.extract_data(data, auth_server_id, policy_id) or []

                with ThreadPoolExecutor(max_workers=10) as executor:
                    futures = {executor.submit(_fetch_policy_rules, p): p for p in policies}
                    for future in as_completed(futures):
                        try:
                            extracted = future.result()
                            if extracted:
                                extracted_data[entity_name].extend(extracted)
                        except Exception as e:
                            logger.exception(f"Error collecting result for auth_server_policy_rules: {str(e)}")

            elif entity_name == "auth_server_clients":
                extracted_data[entity_name] = []
                auth_servers = extracted_data.get("auth_servers", [])

                def _fetch_auth_server_clients(auth_server, _vi=viewset_instance, _req=request):
                    results = []
                    auth_server_id = auth_server.get("auth_server_id")
                    if not auth_server_id:
                        return results
                    clients = _vi.fetch_clients(auth_server_id, request=_req)
                    for client in (clients if isinstance(clients, list) else []):
                        client_id = client.get("client_id") if isinstance(client, dict) else client
                        if not client_id:
                            continue
                        tokens = _vi.fetch_tokens(auth_server_id, client_id, request=_req)
                        extracted = _vi.extract_data(tokens, auth_server_id, client_id)
                        if extracted:
                            results.extend(extracted)
                    return results

                with ThreadPoolExecutor(max_workers=10) as executor:
                    futures = {executor.submit(_fetch_auth_server_clients, auth_server): auth_server for auth_server in auth_servers}
                    for future in as_completed(futures):
                        try:
                            extracted = future.result()
                            if extracted:
                                extracted_data[entity_name].extend(extracted)
                        except Exception as e:
                            logger.exception(f"Error collecting result for auth_server_clients: {str(e)}")

            else:
                extracted_data[entity_name] = []
                auth_servers = extracted_data.get("auth_servers", [])

                def _fetch_auth_server_entity(auth_server, _vi=viewset_instance, _en=entity_name, _req=request):
                    auth_server_id = auth_server.get("auth_server_id")
                    if not auth_server_id:
                        logger.warning("Missing auth_server_id in auth_servers data, skipping.")
                        return []
                    data = _vi.fetch_from_okta(auth_server_id, request=_req)
                    result = _vi.extract_data(data, auth_server_id)
                    if not result:
                        logger.info(f"No {_en} data extracted for auth server {auth_server_id}. Skipping.")
                    return result or []

                with ThreadPoolExecutor(max_workers=10) as executor:
                    futures = {executor.submit(_fetch_auth_server_entity, auth_server): auth_server for auth_server in auth_servers}
                    for future in as_completed(futures):
                        try:
                            extracted = future.result()
                            if extracted:
                                extracted_data[entity_name].extend(extracted)
                        except Exception as e:
                            logger.exception(f"Error collecting result for {entity_name}: {str(e)}")

            logger.info(f"Extracted {len(extracted_data[entity_name])} records for {entity_name}.")

        extracted_data_cleaned = {
            entity: clean_entity_data(entity, data)
            for entity, data in extracted_data.items()
        }

        for entity_name, data in extracted_data_cleaned.items():
            viewset_instance = AUTH_SERVER_ENTITY_VIEWSETS[entity_name]()
            viewset_instance.request = request
            viewset_instance.store_data(data, db_name)

        return extracted_data_cleaned
