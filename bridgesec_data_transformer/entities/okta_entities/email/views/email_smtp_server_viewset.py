import logging

from entities.views.base_view import BaseEntityViewSet
from entities.okta_entities.email.email_models import EmailSmtpServer
from entities.okta_entities.email.email_serializers import EmailSmtpServerSerializer

logger = logging.getLogger(__name__)


class EmailSmtpServerViewSet(BaseEntityViewSet):
    okta_endpoint = "/api/v1/email-servers"
    entity_type = "email_smtp_servers"
    serializer_class = EmailSmtpServerSerializer
    model = EmailSmtpServer

    def extract_data(self, okta_data):
        """Extract and format email SMTP server data from Okta response"""
        formatted_data = []

        items = okta_data if isinstance(okta_data, list) else [okta_data]

        for item in items:
            if not isinstance(item, dict):
                logger.warning(f"Skipping invalid record (not a dict): {item}")
                continue
            formatted_data.append({
                "smtp_id" : item.get("id", ""),
                "alias": item.get("alias", ""),
                "host": item.get("host", ""),
                "port": item.get("port", 587),
                "username": item.get("username", ""),
                "password": item.get("password", ""),
                "enabled": item.get("enabled", False)
            })

        logger.info("Extracted %d Email SMTP Server records", len(formatted_data))
        return formatted_data