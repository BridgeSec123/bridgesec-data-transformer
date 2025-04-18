import logging

from entities.okta_entities.device_assurance_policies.device_assurance_policy_models import (
    DeviceMacOS,
)
from entities.okta_entities.device_assurance_policies.device_assurance_policy_serializers import (
    DeviceMacOSSerializer,
)
from entities.okta_entities.device_assurance_policies.views.device_base_viewset import (
    BaseDeviceAssurancePolicyViewSet,
)

logger = logging.getLogger(__name__)

class DeviceMacOSViewSet(BaseDeviceAssurancePolicyViewSet):
    
    entity = "okta_policy_device_assurance_macos"
    serializer_class = DeviceMacOSSerializer
    model = DeviceMacOS
    
    def extract_data(self, okta_data):
        logger.info("Extracting data from Okta response.")
        # extracted_data = super().extract_data(okta_data)

        formatted_data = []
        for record in okta_data:
            if record.get("platform") == "MACOS":
                third_party_signal_providers = record.get("thirdPartySignalProviders", {})
                formatted_record = {
                    "name": record.get("name"),
                    "os_version": record.get("osVersion", {}).get("minimum", ""),
                    "disk_encryption_type": record.get("diskEncryptionType", {}).get("include", []),
                    "secure_hardware_present": record.get("secureHardwarePresent", False),
                    "screenlock_type": record.get("screenLockType", {}).get("include", []),
                    "third_party_signal_providers": third_party_signal_providers,
                    "tpsp_browser_version": third_party_signal_providers.get("browserVersion", ""),
                    "tpsp_builtin_dns_client_enabled": third_party_signal_providers.get("builtinDnsClientEnabled", False),
                    "tpsp_chrome_remote_desktop_app_blocked": third_party_signal_providers.get("chromeRemoteDesktopAppBlocked", False),
                    "tpsp_device_enrollment_domain": third_party_signal_providers.get("deviceEnrollmentDomain", ""),
                    "tpsp_disk_encrypted": third_party_signal_providers.get("diskEncrypted", False),
                    "tpsp_key_trust_level": third_party_signal_providers.get("keyTrustLevel", ""),
                    "tpsp_os_firewall": third_party_signal_providers.get("osFirewall", False),
                    "tpsp_os_version": third_party_signal_providers.get("osVersion", ""),
                    "tpsp_password_protection_warning_trigger": third_party_signal_providers.get("passwordProtectionWarningTrigger", ""),
                    "tpsp_realtime_url_check_mode": third_party_signal_providers.get("realtimeUrlCheckMode", False),
                    "tpsp_safe_browsing_protection_level": third_party_signal_providers.get("safeBrowsingProtectionLevel", ""),
                    "tpsp_screen_lock_secured": third_party_signal_providers.get("screenLockSecured", False),
                    "tpsp_site_isolation_enabled": third_party_signal_providers.get("siteIsolationEnabled", False),
                }
                formatted_data.append(formatted_record)
        logger.info(f"Extracted and formatted {len(formatted_data)} Device Mac OS records from Okta.")
        return formatted_data