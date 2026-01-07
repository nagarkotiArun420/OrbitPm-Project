from django.db.models import Q
from accounts.models import User
from projects.models import Project

def get_authorized_projects(user):
    """
    Decoupled selector logic to fetch authorized projects for a user.
    Enforces strict role-based visibility rules and applies query optimizations
    (select_related and prefetch_related) to prevent N+1 query patterns.
    """
    if not user or not user.is_authenticated:
        return Project.objects.none()

    # Base optimized query
    queryset = Project.objects.select_related(
        'manager', 'client', 'created_by'
    ).prefetch_related('team_members')

    # ADMIN possesses full visibility of all records
    if user.role == User.Roles.ADMIN:
        return queryset

    # MANAGER sees projects they manage, created, are the client of, or are assigned to
    if user.role == User.Roles.MANAGER:
        return queryset.filter(
            Q(manager=user) | 
            Q(created_by=user) | 
            Q(client=user) | 
            Q(team_members=user)
        ).distinct()

    # DEVELOPER sees projects where they are in team members
    if user.role == User.Roles.DEVELOPER:
        return queryset.filter(team_members=user)

    # CLIENT sees projects where they are the designated client
    if user.role == User.Roles.CLIENT:
        return queryset.filter(client=user)

    return Project.objects.none()
