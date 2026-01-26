from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.utils import timezone

from accounts.models import User
from analytics.selectors import (
    apply_date_range,
    get_analytics_projects_queryset,
    get_analytics_tasks_queryset,
)
from common.constants import TargetType
from common.models import ActivityLog
from invoices.models import Invoice
from projects.constants import ProjectStatus
from projects.models import Project
from tasks.constants import TaskPriority, TaskStatus


def _percentage(part, total):
    if not total:
        return 0.0
    return round((part / total) * 100, 2)


def _distribution(queryset, field_name, choices):
    rows = queryset.values(field_name).annotate(count=Count('id')).order_by()
    counts = {row[field_name]: row['count'] for row in rows}
    total = sum(counts.values())

    return [
        {
            'value': value,
            'label': label,
            'count': counts.get(value, 0),
            'percentage': _percentage(counts.get(value, 0), total),
        }
        for value, label in choices
    ]


def _task_aggregate(queryset, reference_date=None):
    reference_date = reference_date or timezone.localdate()
    overdue_filter = (
        Q(due_date__lt=reference_date, is_archived=False) &
        ~Q(status=TaskStatus.COMPLETED)
    )

    totals = queryset.aggregate(
        total=Count('id', distinct=True),
        completed=Count(
            'id',
            filter=Q(status=TaskStatus.COMPLETED),
            distinct=True,
        ),
        overdue=Count('id', filter=overdue_filter, distinct=True),
        archived=Count('id', filter=Q(is_archived=True), distinct=True),
    )
    total = totals['total'] or 0
    completed = totals['completed'] or 0
    archived = totals['archived'] or 0
    active = queryset.filter(is_archived=False).exclude(
        status=TaskStatus.COMPLETED
    ).count()

    return {
        'total_tasks': total,
        'active_tasks': active,
        'pending_tasks': total - completed,
        'completed_tasks': completed,
        'overdue_tasks': totals['overdue'] or 0,
        'archived_tasks': archived,
        'task_completion_percentage': _percentage(completed, total),
    }


def _assignment_workload(queryset, reference_date=None):
    reference_date = reference_date or timezone.localdate()
    overdue_filter = (
        Q(due_date__lt=reference_date, is_archived=False) &
        ~Q(status=TaskStatus.COMPLETED)
    )
    active_filter = Q(is_archived=False) & ~Q(status=TaskStatus.COMPLETED)

    rows = queryset.values(
        'assigned_to_id',
        'assigned_to__email',
        'assigned_to__full_name',
    ).annotate(
        total_tasks=Count('id', distinct=True),
        active_tasks=Count('id', filter=active_filter, distinct=True),
        completed_tasks=Count(
            'id',
            filter=Q(status=TaskStatus.COMPLETED),
            distinct=True,
        ),
        overdue_tasks=Count('id', filter=overdue_filter, distinct=True),
    ).order_by('assigned_to__full_name', 'assigned_to__email')

    return [
        {
            'user_id': row['assigned_to_id'],
            'email': row['assigned_to__email'],
            'full_name': row['assigned_to__full_name'] or 'Unassigned',
            'total_tasks': row['total_tasks'],
            'active_tasks': row['active_tasks'],
            'completed_tasks': row['completed_tasks'],
            'overdue_tasks': row['overdue_tasks'],
        }
        for row in rows
    ]


def _project_member_counts(projects):
    rows = projects.annotate(
        team_member_count=Count('team_members', distinct=True),
        active_membership_count=Count(
            'memberships',
            filter=Q(memberships__is_active=True),
            distinct=True,
        ),
    ).values(
        'id',
        'slug',
        'title',
        'team_member_count',
        'active_membership_count',
    ).order_by('title')

    member_counts = []
    for row in rows:
        member_count = max(
            row['team_member_count'] or 0,
            row['active_membership_count'] or 0,
        )
        member_counts.append({
            'project_id': row['id'],
            'project_slug': row['slug'],
            'project_title': row['title'],
            'member_count': member_count,
            'active_member_count': member_count,
        })
    return member_counts


def _activity_summary(projects, tasks, date_range=None):
    project_ids = [str(project_id) for project_id in projects.values_list('id', flat=True)]
    task_ids = [str(task_id) for task_id in tasks.values_list('id', flat=True)]

    if not project_ids and not task_ids:
        return {
            'total': 0,
            'project_events': 0,
            'task_events': 0,
        }

    queryset = ActivityLog.objects.filter(
        Q(target_type=TargetType.PROJECT, target_id__in=project_ids) |
        Q(target_type=TargetType.TASK, target_id__in=task_ids)
    )
    queryset = apply_date_range(queryset, date_range, field_name='created_at')

    totals = queryset.aggregate(
        total=Count('id'),
        project_events=Count(
            'id',
            filter=Q(target_type=TargetType.PROJECT),
        ),
        task_events=Count(
            'id',
            filter=Q(target_type=TargetType.TASK),
        ),
    )
    return {
        'total': totals['total'] or 0,
        'project_events': totals['project_events'] or 0,
        'task_events': totals['task_events'] or 0,
    }


def _invoice_metrics(user, date_range=None):
    if user.role in (User.Roles.ADMIN, User.Roles.MANAGER):
        invoices = Invoice.objects.all()
    elif user.role == User.Roles.CLIENT:
        invoices = Invoice.objects.filter(client=user)
    else:
        invoices = Invoice.objects.none()

    invoices = apply_date_range(invoices, date_range, field_name='created_at')
    totals = invoices.aggregate(
        total_revenue=Sum(
            'amount',
            filter=Q(status=Invoice.InvoiceStatus.PAID),
        ),
        unpaid_revenue=Sum(
            'amount',
            filter=~Q(status=Invoice.InvoiceStatus.PAID),
        ),
    )
    return {
        'total_revenue': totals['total_revenue'] or Decimal('0.00'),
        'unpaid_revenue': totals['unpaid_revenue'] or Decimal('0.00'),
    }


def get_dashboard_metrics(user, date_range=None):
    """
    Compile dashboard analytics for the projects and tasks visible to a user.
    """
    date_range = date_range or {
        'period': 'all_time',
        'start_date': None,
        'end_date': None,
        'is_filtered': False,
    }
    projects = get_analytics_projects_queryset(user)
    tasks = get_analytics_tasks_queryset(user)

    projects = apply_date_range(projects, date_range, field_name='created_at')
    tasks = apply_date_range(tasks, date_range, field_name='created_at')

    project_totals = projects.aggregate(
        total=Count('id', distinct=True),
        active=Count(
            'id',
            filter=Q(status=ProjectStatus.IN_PROGRESS),
            distinct=True,
        ),
        completed=Count(
            'id',
            filter=Q(status=ProjectStatus.COMPLETED),
            distinct=True,
        ),
    )
    member_counts = _project_member_counts(projects)
    task_metrics = _task_aggregate(tasks)
    activity = _activity_summary(projects, tasks, date_range=date_range)

    return {
        'date_range': date_range,
        'total_projects': project_totals['total'] or 0,
        'active_projects': project_totals['active'] or 0,
        'completed_projects': project_totals['completed'] or 0,
        'total_project_members': sum(
            item['active_member_count'] for item in member_counts
        ),
        'project_member_counts': member_counts,
        **task_metrics,
        'tasks_by_status': _distribution(tasks, 'status', TaskStatus.choices),
        'tasks_by_priority': _distribution(tasks, 'priority', TaskPriority.choices),
        'assignment_workload': _assignment_workload(tasks),
        'recent_activity_count': activity['total'],
        'recent_activity': activity,
        **_invoice_metrics(user, date_range=date_range),
    }


def get_project_summary(project, user, date_range=None):
    """
    Compile project-scoped task, membership, and activity analytics.
    The task queryset remains scoped by user permissions.
    """
    date_range = date_range or {
        'period': 'all_time',
        'start_date': None,
        'end_date': None,
        'is_filtered': False,
    }
    tasks = get_analytics_tasks_queryset(user).filter(project=project)
    tasks = apply_date_range(tasks, date_range, field_name='created_at')

    project_counts = _project_member_counts(Project.objects.filter(id=project.id))
    active_members = (
        project_counts[0]['active_member_count']
        if project_counts else 0
    )
    task_metrics = _task_aggregate(tasks)
    activity = _activity_summary(
        Project.objects.filter(id=project.id),
        tasks,
        date_range=date_range,
    )

    return {
        'project': {
            'id': project.id,
            'title': project.title,
            'slug': project.slug,
            'status': project.status,
            'priority': project.priority,
        },
        'date_range': date_range,
        **task_metrics,
        'active_members': active_members,
        'tasks_by_status': _distribution(tasks, 'status', TaskStatus.choices),
        'tasks_by_priority': _distribution(tasks, 'priority', TaskPriority.choices),
        'assignment_workload': _assignment_workload(tasks),
        'recent_activity_count': activity['total'],
        'recent_activity': activity,
    }


def calculate_dashboard_metrics(user):
    """
    Backward-compatible wrapper retained for older imports.
    """
    return get_dashboard_metrics(user)
