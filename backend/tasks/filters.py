from django_filters import rest_framework as filters
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
    
    created_at = filters.DateTimeFilter(field_name='created_at')
    created_at_gte = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_at_lte = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')

    class Meta:
        model = Task
        fields = {
            'status': ['exact', 'in'],
            'priority': ['exact', 'in'],
            'assigned_to': ['exact', 'isnull'],
            'project': ['exact'],
        }
