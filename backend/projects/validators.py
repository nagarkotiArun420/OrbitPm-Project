from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal

def validate_date_not_past(value):
    """
    Validates that a date field value is not set in the past relative to the current local date.
    """
    if value and value < timezone.localdate():
        raise ValidationError("The date cannot be set in the past.")

def validate_budget_positive(value):
    """
    Validates that the project budget is a positive amount.
    """
    if value is not None and value < Decimal('0.00'):
        raise ValidationError("Budget must be a non-negative value.")
