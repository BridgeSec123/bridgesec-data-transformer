import logging



from entities.okta_entities.link.views.link_base_viewset import BaseLinkViewSet
from entities.okta_entities.link.link_models import OktaLinkDefinition
from entities.okta_entities.link.link_serializers import OktaLinkDefinitionSerializer

logger = logging.getLogger(__name__)

class OktaLinkDefinitionViewSet(BaseLinkViewSet):
    okta_endpoint = "/api/v1/meta/schemas/user/linkedObjects"
    entity_type = "okta_link_definition"
    serializer_class = OktaLinkDefinitionSerializer
    model = OktaLinkDefinition

    def extract_data(self, okta_data):
        """
        Override to format the user data by removing the "profile" key.
        """
       
        extracted_data = super().extract_data(okta_data)

        logger.info("Extracting data from Okta response")
        formatted_data = []

        
        for record in extracted_data:
            associated = record.get("associated", {})
            primary = record.get("primary", {})
            formatted_data.append(
                {
                    "associated_description": associated.get("description", ""),
                    "associated_title": associated.get("title", ""),
                    "associated_name": associated.get("name", ""),
                    "primary_description": primary.get("description", ""),
                    "primary_title": primary.get("title", ""),
                    "primary_name": primary.get("name", ""),
                }
            )

        logger.info("Extracted and formatted %d link definition records from Okta", len(formatted_data))

        return formatted_data
