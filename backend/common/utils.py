from decimal import Decimal
import uuid

def get_client_ip(request):
    """
    Safely extract client IP address from request headers, handling proxies.
    """
    if not request:
        return None
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def serialize_field_value(value):
    """
    Serialize model instances, UUIDs, Decimals, and other types to JSON-compatible strings.
    """
    if value is None:
        return None
    if hasattr(value, 'pk'):
        if hasattr(value, 'email'):
            return str(value.email)
        elif hasattr(value, 'title'):
            return str(value.title)
        return str(value.pk)
    if isinstance(value, (uuid.UUID, Decimal)):
        return str(value)
    return value

def get_model_changes(instance, validated_data):
    """
    Compare the current model instance and incoming validated data to produce a diff of modifications.
    """
    changes = {}
    for field, value in validated_data.items():
        if not hasattr(instance, field):
            continue
        old_val = getattr(instance, field)
        
        # Avoid direct equality checks on M2M managers
        if hasattr(old_val, 'all') and not hasattr(old_val, 'pk'):
            continue
            
        if old_val != value:
            changes[field] = {
                'old': serialize_field_value(old_val),
                'new': serialize_field_value(value)
            }
    return changes
