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
        # Developers can use safe methods, PATCH, and the custom 'unarchive' POST action
        if request.method in permissions.SAFE_METHODS or request.method == 'PATCH':
            return True
        if getattr(view, 'action', None) == 'unarchive':
            return True
        return False

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


class HasTaskCommentPermission(permissions.BasePermission):
    """
    Role-based permission checks for Task Comments:
    - User must have access to the related Task.
    - ADMIN: full read/write access.
    - MANAGER: full read/write access for tasks in managed/created projects.
    - DEVELOPER: can read/create comments on assigned tasks. Can only edit/delete their own comments.
    - CLIENT: read-only access to tasks in projects where they are the client.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        task_slug = view.kwargs.get('task_slug')
        if not task_slug:
            return False

        from tasks.selectors import get_authorized_tasks
        from tasks.models import Task
        try:
            task = get_authorized_tasks(request.user).get(slug=task_slug)
        except Task.DoesNotExist:
            return False

        # If it's a read-only method:
        if request.method in permissions.SAFE_METHODS:
            return True

        # For write methods:
        # CLIENT is read-only
        if request.user.role == User.Roles.CLIENT:
            return False

        # ADMIN has full write access
        if request.user.role == User.Roles.ADMIN:
            return True

        # MANAGER has write access only if project manager or project creator
        if request.user.role == User.Roles.MANAGER:
            return (
                task.project.manager == request.user or
                task.project.created_by == request.user
            )

        # DEVELOPER can create comments only if the task is assigned to them
        if request.user.role == User.Roles.DEVELOPER:
            return task.assigned_to == request.user

        return False

    def has_object_permission(self, request, view, obj):
        # This checks object-level permissions for PUT, PATCH, DELETE on a specific comment.
        if request.method in permissions.SAFE_METHODS:
            return True

        # ADMIN: full access
        if request.user.role == User.Roles.ADMIN:
            return True

        # MANAGER: delete comments within managed projects, but editing remains author-owned.
        if request.user.role == User.Roles.MANAGER:
            if request.method not in ('DELETE',):
                return False
            return (
                obj.task.project.manager == request.user or
                obj.task.project.created_by == request.user
            )

        # DEVELOPER: can only edit/delete their own comments
        if request.user.role == User.Roles.DEVELOPER:
            return obj.author == request.user

        return False


class HasTaskAttachmentPermission(permissions.BasePermission):
    """
    Role-based permission checks for Task Attachments:
    - User must have access to the related Task.
    - ADMIN: full read/write access.
    - MANAGER: full read/write access for tasks in managed/created projects.
    - DEVELOPER: can upload/delete attachments on tasks assigned to them.
    - CLIENT: read-only access to tasks in projects where they are the client.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        task_slug = view.kwargs.get('task_slug')
        if not task_slug:
            return False

        from django.http import Http404
        from tasks.selectors import get_authorized_tasks
        from tasks.models import Task
        try:
            task = Task.objects.get(slug=task_slug)
        except Task.DoesNotExist:
            raise Http404("Task not found.")
            
        if task.is_deleted:
            raise Http404("Task not found.")
            
        if not get_authorized_tasks(request.user).filter(id=task.id).exists():
            return False

        # SAFE_METHODS (GET, HEAD, OPTIONS)
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write methods: POST (create)
        if request.user.role == User.Roles.CLIENT:
            return False

        if request.user.role == User.Roles.ADMIN:
            return True

        if request.user.role == User.Roles.MANAGER:
            return (
                task.project.manager == request.user or
                task.project.created_by == request.user
            )

        if request.user.role == User.Roles.DEVELOPER:
            return task.assigned_to == request.user

        return False

    def has_object_permission(self, request, view, obj):
        # Checks object-level permissions (e.g. DELETE)
        if request.method in permissions.SAFE_METHODS:
            return True

        if request.user.role == User.Roles.ADMIN:
            return True

        if request.user.role == User.Roles.MANAGER:
            return (
                obj.task.project.manager == request.user or
                obj.task.project.created_by == request.user
            )

        if request.user.role == User.Roles.DEVELOPER:
            return obj.task.assigned_to == request.user

        return False
