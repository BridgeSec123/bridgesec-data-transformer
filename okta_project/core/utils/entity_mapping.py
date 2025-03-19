ENTITY_TYPE_MAPPING = {
    "users": {
        "okta_endpoint": "/api/v1/users",
        "attributes": ["profile"],
    },
    "groups": {
        "okta_endpoint": "/api/v1/groups",
        "attributes": ["profile"],
    }
}

ENTITY_UNIQUE_FIELDS = {
    "users": "email",
    "groups": "name"
}

def get_unique_field(entity_type):
    """Return the unique field for a given entity type."""
    return ENTITY_UNIQUE_FIELDS.get(entity_type, "_id")

def get_nested_value(data, attribute_path):
    """
    Retrieve a nested value from a dictionary based on a given attribute path.
    
    :param data: The dictionary (JSON response from Okta).
    :param attribute_path: The attribute path (e.g., "profile.firstName").
    :return: The extracted value or None if not found.
    """
    keys = attribute_path.split(".")
    for key in keys:
        if isinstance(data, dict) and key in data:
            data = data[key]
        else:
            return None
    return data

def extract_entity_data(entity_type, okta_data):
    """
    Generic method to extract relevant data based on entity type.

    :param entity_type: Type of entity (user, group, application)
    :param okta_data: List of JSON records from Okta API response
    :return: Extracted data list
    """
    if entity_type not in ENTITY_TYPE_MAPPING:
        return {"error": f"Invalid entity type: {entity_type}"}

    attributes = ENTITY_TYPE_MAPPING[entity_type]["attributes"]

    extracted_data = []
    for record in okta_data:
        if isinstance(record, dict):
            extracted_record = {attr: get_nested_value(record, attr) for attr in attributes}
            extracted_data.append(extracted_record)
    return extracted_data