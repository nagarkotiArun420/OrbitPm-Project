from rest_framework import permissions
from accounts.models import User

class HasProjectPermission(permissions.BasePermission):
    """
    Role-based object-level permission for OrbitPM Projects.
    - ADMIN: Full access to all projects.
    - MANAGER: Can create projects, and edit/delete projects they manage or created.
    - DEVELOPER: View-only access to projects where they are in team_members.
    - CLIENT: View-only access to projects where they are mapped as the client.
    """

    def has_permission(self, request, view):
        # Must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False

        # Only Admins and Managers are allowed to create projects
        if request.method == 'POST':
            return request.user.role in [User.Roles.ADMIN, User.Roles.MANAGER]

        return True

    def has_object_permission(self, request, view, obj):
        user = request.user

        # ADMIN possesses full permission on all records
        if user.role == User.Roles.ADMIN:
            return True

        is_safe = request.method in permissions.SAFE_METHODS

        # MANAGER Rules:
        # - Can view project if they manage it, created it, or are assigned as team/client
        # - Can edit/delete project only if they manage it or created it
        if user.role == User.Roles.MANAGER:
            is_manager_or_creator = (obj.manager == user or obj.created_by == user)
            if is_safe:
                return (
                    is_manager_or_creator or 
                    obj.client == user or 
                    obj.team_members.filter(id=user.id).exists()
                )
            return is_manager_or_creator

        # DEVELOPER Rules:
        # - Read-only (SAFE_METHODS)
        # - Must be a team member of the project
        if user.role == User.Roles.DEVELOPER:
            if not is_safe:
                return False
            return obj.team_members.filter(id=user.id).exists()

        # CLIENT Rules:
        # - Read-only (SAFE_METHODS)
        # - Must be the designated client of the project
        if user.role == User.Roles.CLIENT:
            if not is_safe:
                return False
            return obj.client == user

        return False
