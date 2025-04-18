from mongoengine import StringField, ListField, BooleanField

from entities.models.base import BaseEntityModel


class DeviceAndroid(BaseEntityModel):
    name = StringField(required=True)
    os_version = StringField(null=True, required=False)
    disk_encryption_type = ListField(StringField(), null=True, required=False)
    jailbreak = BooleanField(null=True, required=False)
    secure_hardware_present = BooleanField(null=True, required=False)
    screenlock_type = ListField(StringField(), null=True, required=False)
    
    meta = {"collection": "okta_policy_device_assurance_android"}

class DeviceIos(BaseEntityModel):
    name = StringField(required=True)
    os_version = StringField(null=True, required=False)
    jailbreak = BooleanField(null=True, required=False)
    screenlock_type = ListField(StringField(), null=True, required=False)
    
    meta = {"collection": "okta_policy_device_assurance_ios"}

class DeviceMacOS(BaseEntityModel):
    name = StringField(required=True)
    os_version = StringField(null=True, required=False)
    disk_encryption_type = ListField(StringField(), null=True, required=False)
    secure_hardware_present = BooleanField(null=True, required=False)
    screenlock_type = ListField(StringField(), null=True, required=False)
    third_party_signal_providers = BooleanField(null=True, required=False)
    tpsp_browser_version = StringField(null=True, required=False)
    tpsp_builtin_dns_client_enabled = BooleanField(null=True, required=False)
    tpsp_chrome_remote_desktop_app_blocked = BooleanField(null=True, required=False)
    tpsp_device_enrollment_domain = StringField(null=True, required=False)
    tpsp_disk_encrypted = BooleanField(null=True, required=False)
    tpsp_key_trust_level = StringField(null=True, required=False)
    tpsp_os_firewall = BooleanField(null=True, required=False)
    tpsp_os_version = StringField(null=True, required=False)
    tpsp_password_protection_warning_trigger = StringField(null=True, required=False)
    tpsp_realtime_url_check_mode = BooleanField(null=True, required=False)
    tpsp_safe_browsing_protection_level = StringField(null=True, required=False)
    tpsp_screen_lock_secured = BooleanField(null=True, required=False)
    tpsp_site_isolation_enabled = BooleanField(null=True, required=False)
    
    meta = {"collection": "okta_policy_device_assurance_macos"}

class DeviceWindows(BaseEntityModel):
    name = StringField(required=True)
    os_version = StringField(null=True, required=False)
    secure_hardware_present = BooleanField(null=True, required=False)
    screenlock_type = ListField(StringField(), null=True, required=False)
    disk_encryption_type = ListField(StringField(), null=True, required=False)
    third_party_signal_providers = BooleanField(null=True, required=False)
    tpsp_browser_version = StringField(null=True, required=False)
    tpsp_builtin_dns_client_enabled = BooleanField(null=True, required=False)
    tpsp_chrome_remote_desktop_app_blocked = BooleanField(null=True, required=False)
    tpsp_crowd_strike_agent_id = StringField(null=True, required=False)
    tpsp_crowd_strike_customer_id = StringField(null=True, required=False)
    tpsp_device_enrollment_domain = StringField(null=True, required=False)
    tpsp_disk_encrypted = BooleanField(null=True, required=False)
    tpsp_key_trust_level = StringField(null=True, required=False)
    tpsp_os_firewall = BooleanField(null=True, required=False)
    tpsp_os_version = StringField(null=True, required=False)
    tpsp_password_protection_warning_trigger = StringField(null=True, required=False)
    tpsp_realtime_url_check_mode = BooleanField(null=True, required=False)
    tpsp_safe_browsing_protection_level = StringField(null=True, required=False)
    tpsp_screen_lock_secured = BooleanField(null=True, required=False)
    tpsp_secure_boot_enabled = BooleanField(null=True, required=False)
    tpsp_site_isolation_enabled = BooleanField(null=True, required=False)
    tpsp_third_party_blocking_enabled = BooleanField(null=True, required=False)
    tpsp_windows_machine_domain = StringField(null=True, required=False)
    tpsp_windows_user_domain = StringField(null=True, required=False)
    
    meta = {"collection": "okta_policy_device_assurance_windows"}
