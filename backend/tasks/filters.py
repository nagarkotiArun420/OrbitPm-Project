from django_filters import rest_framework as filters
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from tasks.constants import TaskStatus
from tasks.models import Task

class TaskFilter(filters.FilterSet):
    """
    Custom FilterSet for Tasks.
    Supports equality and range filters for dates/timestamps,
    exact and collection matching for categories and relations.
    """
    due_date = filters.DateFilter(field_name='due_date')
    due_date_gte = filters.DateFilter(field_name='due_date', lookup_expr='gte')
    due_date_lte = filters.DateFilter(field_name='due_date', lookup_expr='lte')
    overdue = filters.BooleanFilter(method='filter_overdue')
    due_today = filters.BooleanFilter(method='filter_due_today')
    upcoming_deadlines = filters.BooleanFilter(method='filter_upcoming_deadlines')
    upcoming_days = filters.NumberFilter(method='filter_upcoming_days')
    
    created_at = filters.DateTimeFilter(field_name='created_at')
    created_at_gte = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_at_lte = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')

    def filter_overdue(self, queryset, name, value):
        if value is True:
            return queryset.overdue()
        if value is False:
            reference_date = timezone.localdate()
            return queryset.exclude(
                Q(due_date__lt=reference_date, is_archived=False, is_deleted=False) & 
                ~Q(status=TaskStatus.COMPLETED)
            )
        return queryset

    def filter_due_today(self, queryset, name, value):
        if value is True:
            return queryset.due_today()
        if value is False:
            reference_date = timezone.localdate()
            return queryset.exclude(
                Q(due_date=reference_date, is_archived=False, is_deleted=False) & 
                ~Q(status=TaskStatus.COMPLETED)
            )
        return queryset

    def filter_upcoming_deadlines(self, queryset, name, value):
        if value is True:
            return queryset.upcoming_deadlines()
        if value is False:
            reference_date = timezone.localdate()
            end_date = reference_date + timedelta(days=3)
            return queryset.exclude(
                Q(due_date__gt=reference_date, due_date__lte=end_date, is_archived=False, is_deleted=False) & 
                ~Q(status=TaskStatus.COMPLETED)
            )
        return queryset

    def filter_upcoming_days(self, queryset, name, value):
        try:
            days = int(value)
        except (TypeError, ValueError):
            return queryset.none()
        if days < 0:
            return queryset.none()
        return queryset.upcoming_deadlines(days=days)

    class Meta:
        model = Task
        fields = {
            'status': ['exact', 'in'],
            'priority': ['exact', 'in'],
            'assigned_to': ['exact', 'isnull'],
            'project': ['exact'],
            'is_archived': ['exact'],
        }
