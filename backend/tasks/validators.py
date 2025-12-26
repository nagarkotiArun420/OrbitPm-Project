from django.core.exceptions import ValidationError

def validate_hours_non_negative(value):
    """
    Ensures that hours estimated or actual are not a negative value.
    """
    if value is not None and value < 0:
        raise ValidationError("Hours cannot be negative.")
