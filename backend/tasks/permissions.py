from rest_framework import permissions
from accounts.models import User


class IsTaskAdmin(permissions.BasePermission):
    """
    ADMIN: full access to all task operations.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role == User.Roles.ADMIN
        )

    def has_object_permission(self, request, view, obj):
        return True


class IsTaskProjectManager(permissions.BasePermission):
    """
    MANAGER:
    - create tasks in managed projects
    - view/update/delete tasks for projects they manage or created
    """
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role == User.Roles.MANAGER
        )

    def has_object_permission(self, request, view, obj):
        # Manager can operate on tasks in projects they manage or created
        return (
            obj.project.manager == request.user or
            obj.project.created_by == request.user
        )


class IsTaskDeveloper(permissions.BasePermission):
    """
    DEVELOPER:
    - view assigned tasks (GET, HEAD, OPTIONS)
    - update task progress/status on assigned tasks (PATCH only)
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated and
                request.user.role == User.Roles.DEVELOPER):
            return False
        # Developers can use safe methods and PATCH (for updating progress)
        return request.method in permissions.SAFE_METHODS or request.method == 'PATCH'

    def has_object_permission(self, request, view, obj):
        # Developer can only access tasks assigned to them
        return obj.assigned_to == request.user


class IsTaskClient(permissions.BasePermission):
    """
    CLIENT:
    - read-only access to tasks in projects where they are the designated client
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated and
                request.user.role == User.Roles.CLIENT):
            return False
        return request.method in permissions.SAFE_METHODS

    def has_object_permission(self, request, view, obj):
        # Client can only view tasks for projects they are the client of
        return obj.project.client == request.user


class HasTaskPermission(permissions.BasePermission):
    """
    Composite permission dispatcher for the Tasks module.
    Delegates permission checks to the appropriate role-specific class
    based on the authenticated user's role.
    """
    _role_permission_map = {
        User.Roles.ADMIN: IsTaskAdmin,
        User.Roles.MANAGER: IsTaskProjectManager,
        User.Roles.DEVELOPER: IsTaskDeveloper,
        User.Roles.CLIENT: IsTaskClient,
    }

    def _get_role_permission(self, request):
        """Resolve the appropriate permission class for the user's role."""
        if not request.user or not request.user.is_authenticated:
            return None
        perm_class = self._role_permission_map.get(request.user.role)
        return perm_class() if perm_class else None

    def has_permission(self, request, view):
        perm = self._get_role_permission(request)
        if perm is None:
            return False
        return perm.has_permission(request, view)

    def has_object_permission(self, request, view, obj):
        perm = self._get_role_permission(request)
        if perm is None:
            return False
        return perm.has_object_permission(request, view, obj)
