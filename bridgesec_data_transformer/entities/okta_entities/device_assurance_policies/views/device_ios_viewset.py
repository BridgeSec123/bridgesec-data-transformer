import logging

from entities.okta_entities.device_assurance_policies.device_assurance_policy_models import (
    DeviceIos,
)
from entities.okta_entities.device_assurance_policies.device_assurance_policy_serializers import (
    DeviceIosSerializer,
)
from entities.okta_entities.device_assurance_policies.views.device_base_viewset import (
    BaseDeviceAssurancePolicyViewSet,
)

logger = logging.getLogger(__name__)

class DeviceIOSViewSet(BaseDeviceAssurancePolicyViewSet):
    
    entity = "okta_policy_device_assurance_ios"
    serializer_class = DeviceIosSerializer
    model = DeviceIos
    
    def extract_data(self, okta_data):
        logger.info("Extracting data from Okta response.")
        # extracted_data = super().extract_data(okta_data)

        formatted_data = []
        for record in okta_data:
            if record.get("platform") == "IOS":
                formatted_record = {
                    "name": record.get("name"),
                    "os_version": record.get("osVersion", {}).get("minimum", ""),
                    "jailbreak": record.get("jailbreak", False),
                    "screenlock_type": record.get("screenLockType", {}).get("include", []),
                }
                formatted_data.append(formatted_record)
        logger.info(f"Extracted and formatted {len(formatted_data)} Device IOS records from Okta.")
        return formatted_data