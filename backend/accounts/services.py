from django.contrib.auth import get_user_model

User = get_user_model()

def create_user_profile(email, password, full_name, role=User.Roles.DEVELOPER, phone_number=None):
    """
    Domain service for user registration.
    Decouples business logic from Django models/serializers, making it easy
    to plug in background workers, welcome emails, or analytics triggers.
    """
    user = User.objects.create_user(
        email=email,
        password=password,
        full_name=full_name,
        role=role,
        phone_number=phone_number
    )
    # Placeholder for post-creation actions:
    # 1. Send welcome notification
    # 2. Initialize default settings or billing profile
    return user
