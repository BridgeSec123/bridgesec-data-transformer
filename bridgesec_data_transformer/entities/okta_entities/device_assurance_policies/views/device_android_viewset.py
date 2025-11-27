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
        formatted_data = []
        for record in okta_data:
            if not isinstance(record, dict):
                continue
            if record.get("platform") == "ANDROID":
                formatted_record = {
                    "device_id": record.get("id", ""),
                    "name": record.get("name"),
                    "os_version": record.get("osVersion", {}).get("minimum", ""),
                    "disk_encryption_type": record.get("diskEncryptionType", {}).get("include", []),
                    "jailbreak": record.get("jailbreak", False),
                    "secure_hardware_present": record.get("secureHardwarePresent", False),
                    "screenlock_type": record.get("screenLockType", {}).get("include", []),
                }
                formatted_data.append(formatted_record)
        logger.info("Extracted %d Device Android records", len(formatted_data))
        return formatted_data