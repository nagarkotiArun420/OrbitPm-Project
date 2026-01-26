from rest_framework import permissions
from accounts.models import User

class CanAccessAnalytics(permissions.BasePermission):
    """
    Allows authenticated OrbitPM users to access analytics scoped by selectors.
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in User.Roles.values
        )
