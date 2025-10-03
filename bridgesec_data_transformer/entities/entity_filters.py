# Common filtering logic for all entities

# App labels to exclude from data extraction
EXCLUDED_APP_LABELS = [
    "Okta Access Requests",
    "Okta Workflows",
    "LDAP Interface",
    "Okta Dashboard",
    "Okta Browser Plugin",
    "Okta Admin Console",
    "Okta Identity Governance",
    "Okta Access Certification Reviews"
]

EXCLUDED_SAML_LABELS = [
    "Workday"
]

# Three Field App labels to exclude from data extraction
EXCLUDED_THREE_FIELD_LABELS = [
    "Microsoft Office 365",
    "Microsoft Office 365 (4)",
    "Microsoft Office 365 (5)"
]

# Group names to exclude from data extraction
EXCLUDED_GROUP_NAMES = [
    "Read-only Domain Controllers",
    "Domain Controllers",
    "DnsUpdateProxy",
    "Allowed RODC Password Replication Group",
    "Protected Users",
    "Cert Publishers",
    "Schema Admins",
    "RAS and IAS Servers",
    "Key Admins",
    "Domain Computers",
    "Enterprise Admins",
    "Cloneable Domain Controllers",
    "Enterprise Key Admins",
    "Domain Admins",
    "Enterprise Read-only Domain Controllers",
    "Group Policy Creator Owners",
    "Denied RODC Password Replication Group",
    "Domain Users",
    "DnsAdmins",
    "Domain Guests"
    ]

# Policy names to exclude from data extraction
EXCLUDED_POLICY_NAMES = [
    "Default Policy",
    "default-policy",
    "Active Directory Policy"
]

# Policy rule names to exclude from data extraction
EXCLUDED_POLICY_RULE_NAMES = [
    "Default Rule",
    "default-rule",
]

# App Signon Policy names to exclude from data extraction
EXCLUDED_APP_SIGNON_POLICY_NAMES = [
    "Okta Account Management Policy",
    "Okta Admin Console"
]

# Network Zone names to exclude from data extraction
EXCLUDED_NETWORK_ZONE_NAMES = [
    "DefaultEnhancedDynamicZone",
    "DefaultExemptIpZone"
]

def should_skip_app_extraction(app_label):
    """
    Check if an app should be skipped based on its label.

    Args:
        app_label (str): The label of the app to check

    Returns:
        bool: True if the app should be skipped, False otherwise
    """
    if not app_label:
        return False

    return app_label in EXCLUDED_APP_LABELS

def should_skip_app_saml_extraction(app_label):
    """
    Check if an app should be skipped based on its label.

    Args:
        app_label (str): The label of the app to check

    Returns:
        bool: True if the app should be skipped, False otherwise
    """
    if not app_label:
        return False

    return app_label in EXCLUDED_SAML_LABELS

def should_skip_group_extraction(group_name):
    """
    Check if a group should be skipped based on its name.

    Args:
        group_name (str): The name of the group to check

    Returns:
        bool: True if the group should be skipped, False otherwise
    """
    if not group_name:
        return False

    return group_name in EXCLUDED_GROUP_NAMES

def should_skip_policy_extraction(policy_name):
    """
    Check if a policy should be skipped based on its name.

    Args:
        policy_name (str): The name of the policy to check

    Returns:
        bool: True if the policy should be skipped, False otherwise
    """
    if not policy_name:
        return False

    return policy_name in EXCLUDED_POLICY_NAMES

def should_skip_policy_rule_extraction(rule_name):
    """
    Check if a policy rule should be skipped based on its name.

    Args:
        rule_name (str): The name of the policy rule to check

    Returns:
        bool: True if the policy rule should be skipped, False otherwise
    """
    if not rule_name:
        return False

    return rule_name in EXCLUDED_POLICY_RULE_NAMES

def should_skip_app_signon_policy_extraction(policy_name):
    """
    Check if an app signon policy should be skipped based on its name.

    Args:
        policy_name (str): The name of the app signon policy to check

    Returns:
        bool: True if the app signon policy should be skipped, False otherwise
    """
    if not policy_name:
        return False

    return policy_name in EXCLUDED_APP_SIGNON_POLICY_NAMES

def should_skip_network_zone_extraction(zone_name):
    """
    Check if a network zone should be skipped based on its name.

    Args:
        zone_name (str): The name of the network zone to check

    Returns:
        bool: True if the network zone should be skipped, False otherwise
    """
    if not zone_name:
        return False

    return zone_name in EXCLUDED_NETWORK_ZONE_NAMES

def should_skip_app_three_field_extraction(app_label):
    """
    Check if a three field app should be skipped based on its label.

    Args:
        app_label (str): The label of the app to check

    Returns:
        bool: True if the app should be skipped, False otherwise
    """
    if not app_label:
        return False

    return app_label in EXCLUDED_THREE_FIELD_LABELS