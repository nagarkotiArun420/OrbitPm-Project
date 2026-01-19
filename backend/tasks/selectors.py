from django.db.models import Q
from accounts.models import User
from tasks.models import Task


def _get_optimized_base_queryset(action='detail'):
    """
    Returns a base Task queryset with select_related and prefetch_related
    applied to prevent N+1 query patterns on list and detail endpoints.
    """
    if action == 'list':
        return Task.objects.select_related(
            'project',
            'assigned_to',
        ).defer('description')

    return Task.objects.select_related(
        'project',
        'project__manager',
        'project__client',
        'project__created_by',
        'assigned_to',
        'assigned_by',
    ).prefetch_related(
        'project__team_members',
    )


def get_authorized_tasks(user, action='detail'):
    """
    Decoupled selector that returns task querysets scoped by user role.
    Enforces strict data isolation so each role sees only authorized records.

    - ADMIN:     full visibility of all tasks
    - MANAGER:   tasks in projects they manage or created
    - DEVELOPER: tasks assigned to them
    - CLIENT:    tasks in projects where they are the designated client
    """
    if not user or not user.is_authenticated:
        return Task.objects.none()

    queryset = _get_optimized_base_queryset(action)

    if user.role == User.Roles.ADMIN:
        return queryset

    if user.role == User.Roles.MANAGER:
        return queryset.filter(
            Q(project__manager=user) |
            Q(project__created_by=user)
        ).distinct()

    if user.role == User.Roles.DEVELOPER:
        return queryset.filter(assigned_to=user)

    if user.role == User.Roles.CLIENT:
        return queryset.filter(project__client=user)

    return Task.objects.none()


def get_task_detail(slug):
    """
    Fetches a single task by slug with full query optimizations applied.
    Used by the detail endpoint to avoid redundant DB hits on nested relations.
    """
    return _get_optimized_base_queryset('detail').get(slug=slug)

