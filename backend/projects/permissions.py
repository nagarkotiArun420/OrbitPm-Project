from rest_framework import permissions
from accounts.models import User

class IsAdmin(permissions.BasePermission):
    """
    ADMIN: full access to all project operations.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role == User.Roles.ADMIN
        )

    def has_object_permission(self, request, view, obj):
        return True


class IsProjectManager(permissions.BasePermission):
    """
    MANAGER:
    - create projects (has_permission POST)
    - update assigned projects (has_object_permission)
    - view assigned projects (has_object_permission)
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role == User.Roles.MANAGER
        )

    def has_object_permission(self, request, view, obj):
        # Manager is authorized to view or edit if they manage it or created it.
        return obj.manager == request.user or obj.created_by == request.user


class IsAssignedDeveloper(permissions.BasePermission):
    """
    DEVELOPER:
    - read-only access to assigned projects
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated and request.user.role == User.Roles.DEVELOPER):
            return False
        return request.method in permissions.SAFE_METHODS

    def has_object_permission(self, request, view, obj):
        # Developer is authorized to view if they are in the team_members
        return obj.team_members.filter(id=request.user.id).exists()


class IsProjectClient(permissions.BasePermission):
    """
    CLIENT:
    - read-only access to projects where they are the client
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated and request.user.role == User.Roles.CLIENT):
            return False
        return request.method in permissions.SAFE_METHODS

    def has_object_permission(self, request, view, obj):
        # Client is authorized to view if they are the designated client
        return obj.client == request.user


class HasProjectPermission(permissions.BasePermission):
    """
    Legacy composite permission class for Projects module.
    Delegates checks to the modular permission classes.
    """
    def has_permission(self, request, view):
        return (
            IsAdmin().has_permission(request, view) or
            IsProjectManager().has_permission(request, view) or
            IsAssignedDeveloper().has_permission(request, view) or
            IsProjectClient().has_permission(request, view)
        )

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
            
        if user.role == User.Roles.ADMIN:
            return IsAdmin().has_object_permission(request, view, obj)
        elif user.role == User.Roles.MANAGER:
            return IsProjectManager().has_object_permission(request, view, obj)
        elif user.role == User.Roles.DEVELOPER:
            return IsAssignedDeveloper().has_object_permission(request, view, obj)
        elif user.role == User.Roles.CLIENT:
            return IsProjectClient().has_object_permission(request, view, obj)
            
        return False


class IsMemberManagerOrReadOnly(permissions.BasePermission):
    """
    Permission for project member management endpoints.
    ADMIN: full access.
    MANAGER: manage members in projects they own (manager or created_by).
    DEVELOPER/CLIENT: read-only access to member lists.
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False

        # Read-only for safe methods (GET, HEAD, OPTIONS)
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write access requires ADMIN or MANAGER role
        return request.user.role in (User.Roles.ADMIN, User.Roles.MANAGER)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        # Read-only for safe methods
        if request.method in permissions.SAFE_METHODS:
            return True

        # ADMIN has full access
        if user.role == User.Roles.ADMIN:
            return True

        # MANAGER can manage members only in projects they manage or created
        if user.role == User.Roles.MANAGER:
            project = obj.project if hasattr(obj, 'project') else obj
            return project.manager == user or project.created_by == user

        return False

