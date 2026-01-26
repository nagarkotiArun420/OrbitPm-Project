from datetime import datetime, time

from django.utils import timezone

from projects.selectors import get_authorized_projects
from tasks.selectors import get_authorized_tasks


def get_analytics_projects_queryset(user):
    """
    Return projects visible to the user with lightweight read optimizations.
    """
    return get_authorized_projects(user, action='list')


def get_analytics_tasks_queryset(user):
    """
    Return non-deleted tasks visible to the user for analytics aggregation.
    Archived tasks remain included so archive metrics can be reported.
    """
    return get_authorized_tasks(user, action='list').filter(is_deleted=False)


def get_project_for_analytics(user, slug):
    """
    Return a project scoped by the standard project authorization selector.
    """
    return get_authorized_projects(user, action='detail').filter(slug=slug).first()


def apply_date_range(queryset, date_range, field_name='created_at', is_datetime=True):
    """
    Apply an inclusive date range to a queryset when a range is requested.
    """
    if not date_range or not date_range.get('is_filtered'):
        return queryset

    start_date = date_range.get('start_date')
    end_date = date_range.get('end_date')
    if not start_date or not end_date:
        return queryset

    if not is_datetime:
        return queryset.filter(**{
            f'{field_name}__gte': start_date,
            f'{field_name}__lte': end_date,
        })

    current_timezone = timezone.get_current_timezone()
    start_at = timezone.make_aware(
        datetime.combine(start_date, time.min),
        current_timezone,
    )
    end_at = timezone.make_aware(
        datetime.combine(end_date, time.max),
        current_timezone,
    )
    return queryset.filter(**{
        f'{field_name}__gte': start_at,
        f'{field_name}__lte': end_at,
    })
