from rest_framework import permissions

class IsTeamManagerOrAdmin(permissions.BasePermission):
    """
    Object-level permission to allow team managers or admins to modify teams.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.manager == request.user or request.user.role == 'ADMIN'
