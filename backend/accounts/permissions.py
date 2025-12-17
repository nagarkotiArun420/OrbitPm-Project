from rest_framework import permissions

class IsAdminUserRole(permissions.BasePermission):
    """
    Allows access only to Admin role.
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'ADMIN'
        )

class IsManagerUserRole(permissions.BasePermission):
    """
    Allows access to Managers and Admins.
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['ADMIN', 'MANAGER']
        )

class IsDeveloperUserRole(permissions.BasePermission):
    """
    Allows access to Developers, Managers, and Admins.
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['ADMIN', 'MANAGER', 'DEVELOPER']
        )

class IsClientUserRole(permissions.BasePermission):
    """
    Allows access to Clients and Admins.
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['ADMIN', 'CLIENT']
        )
