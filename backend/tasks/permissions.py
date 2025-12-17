from rest_framework import permissions

class IsTaskAssigneeOrProjectManager(permissions.BasePermission):
    """
    Object-level permission to allow assignee or project owner to manage a task.
    """
    def has_object_permission(self, request, view, obj):
        # Allow Safe methods for authenticated users
        if request.method in permissions.SAFE_METHODS:
            return True

        # Check if user is the assignee or project owner
        return obj.assigned_to == request.user or obj.project.owner == request.user
