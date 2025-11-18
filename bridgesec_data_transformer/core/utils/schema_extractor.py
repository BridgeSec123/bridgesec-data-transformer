"""
Schema extraction utility to auto-generate UI-friendly field names from MongoEngine models.
Used for dynamic form generation in frontend.
"""


def _convert_to_ui_name(backend_field_name):
    """
    Convert backend field name to UI-friendly name.
    Example: 'app_id' -> 'App Id', 'redirect_uris' -> 'Redirect Uris'
    """
    return backend_field_name.replace("_", " ").title()


def get_ui_backend_mapping(model_class):
    """
    Generate mapping of UI names to backend field names.

    Args:
        model_class: MongoEngine Document class

    Returns:
        dict: {"App Id": "app_id", "Label": "label", ...}
    """
    mapping = {}
    for field_name in model_class._fields.keys():
        if field_name not in ["id", "_id"]:
            ui_name = _convert_to_ui_name(field_name)
            mapping[ui_name] = field_name
    return mapping
