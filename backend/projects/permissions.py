from rest_framework import permissions

class IsProjectOwnerOrReadOnly(permissions.BasePermission):
    """
    Object-level permission to only allow owners of a project to edit it.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Instance must be owned by the requesting user
        return obj.owner == request.user
