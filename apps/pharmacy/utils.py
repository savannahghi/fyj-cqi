# utils.py

from django.core.exceptions import ValidationError


def handle_foreign_keys(request, instance, foreign_key_mapping):
    """
    Handle foreign key relationships for a given instance.

    Args:
    request: The HTTP request object.
    instance: The model instance being updated.
    foreign_key_mapping: Dictionary mapping field names to model classes.

    Returns:
    The updated instance.
    """
    # Store foreign key IDs in session
    if request.method == "GET":
        for key in foreign_key_mapping.keys():
            try:
                request.session[f'{key}_id'] = str(getattr(instance, key).id)
            except AttributeError:
                request.session[f'{key}_id'] = None

    # Set foreign key relationships
    if request.method == "POST":
        for key, model_class in foreign_key_mapping.items():
            model_id = request.session.get(f"{key}_id")
            try:
                if model_id:
                    foreign_obj, created = model_class.objects.get_or_create(id=str(model_id))
                    setattr(instance, key, foreign_obj)
                else:
                    setattr(instance, key, None)
            except (ValidationError, KeyError):
                setattr(instance, key, None)

    return instance
