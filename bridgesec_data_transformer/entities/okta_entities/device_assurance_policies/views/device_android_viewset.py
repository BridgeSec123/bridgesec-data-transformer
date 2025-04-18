import logging

from entities.okta_entities.device_assurance_policies.device_assurance_policy_models import (
    DeviceAndroid,
)
from entities.okta_entities.device_assurance_policies.device_assurance_policy_serializers import (
    DeviceAndroidSerializer,
)
from entities.okta_entities.device_assurance_policies.views.device_base_viewset import (
    BaseDeviceAssurancePolicyViewSet,
)

logger = logging.getLogger(__name__)

class DeviceAndroidViewSet(BaseDeviceAssurancePolicyViewSet):
    
    entity = "okta_policy_device_assurance_android"
    serializer_class = DeviceAndroidSerializer
    model = DeviceAndroid
    
    def extract_data(self, okta_data):
        logger.info("Extracting data from Okta response.")
        # extracted_data = super().extract_data(okta_data)

        formatted_data = []
        for record in okta_data:
            if record.get("platform") == "ANDROID":
                formatted_record = {
                    "name": record.get("name"),
                    "os_version": record.get("osVersion", {}).get("minimum", ""),
                    "disk_encryption_type": record.get("diskEncryptionType", {}).get("include", []),
                    "jailbreak": record.get("jailbreak", False),
                    "secure_hardware_present": record.get("secureHardwarePresent", False),
                    "screenlock_type": record.get("screenLockType", {}).get("include", []),
                }
                formatted_data.append(formatted_record)
        logger.info(f"Extracted and formatted {len(formatted_data)} Device Android records from Okta.")
        return formatted_data