from rest_framework import permissions

class CanAccessAnalytics(permissions.BasePermission):
    """
    Limits high-level system analytics views to internal company staff.
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['ADMIN', 'MANAGER', 'DEVELOPER']
        )
