from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers


class AnalyticsDateRangeQuerySerializer(serializers.Serializer):
    """
    Validates analytics date range query parameters.

    Supported examples:
    - ?period=last_7_days
    - ?period=last_30_days
    - ?period=custom&start_date=2026-05-01&end_date=2026-05-20
    """
    PERIOD_ALIASES = {
        'all': 'all_time',
        'all_time': 'all_time',
        '7': 'last_7_days',
        '7d': 'last_7_days',
        'last_7': 'last_7_days',
        'last 7 days': 'last_7_days',
        'last7days': 'last_7_days',
        'last-7-days': 'last_7_days',
        'last_7_days': 'last_7_days',
        '30': 'last_30_days',
        '30d': 'last_30_days',
        'last_30': 'last_30_days',
        'last 30 days': 'last_30_days',
        'last30days': 'last_30_days',
        'last-30-days': 'last_30_days',
        'last_30_days': 'last_30_days',
        'custom': 'custom',
    }

    period = serializers.CharField(required=False, allow_blank=True)
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)

    def to_internal_value(self, data):
        normalized_data = data.copy()
        if 'period' not in normalized_data:
            for alias in ('range', 'date_range'):
                if alias in normalized_data:
                    normalized_data['period'] = normalized_data[alias]
                    break
        return super().to_internal_value(normalized_data)

    def validate(self, attrs):
        today = timezone.localdate()
        raw_period = (attrs.get('period') or '').strip().lower()
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')

        if not raw_period and (start_date or end_date):
            raw_period = 'custom'

        period = self.PERIOD_ALIASES.get(raw_period or 'all_time')
        if period is None:
            raise serializers.ValidationError({
                'period': 'Use all_time, last_7_days, last_30_days, or custom.'
            })

        if period == 'last_7_days':
            start_date = today - timedelta(days=6)
            end_date = today
        elif period == 'last_30_days':
            start_date = today - timedelta(days=29)
            end_date = today
        elif period == 'custom':
            if not start_date or not end_date:
                raise serializers.ValidationError({
                    'date_range': 'Custom analytics ranges require start_date and end_date.'
                })
            if start_date > end_date:
                raise serializers.ValidationError({
                    'date_range': 'start_date must be on or before end_date.'
                })
        else:
            start_date = None
            end_date = None

        attrs['period'] = period
        attrs['start_date'] = start_date
        attrs['end_date'] = end_date
        attrs['is_filtered'] = period != 'all_time'
        return attrs


class AnalyticsDateRangeSerializer(serializers.Serializer):
    period = serializers.CharField()
    start_date = serializers.DateField(allow_null=True)
    end_date = serializers.DateField(allow_null=True)
    is_filtered = serializers.BooleanField()


class ChartBucketSerializer(serializers.Serializer):
    value = serializers.CharField()
    label = serializers.CharField()
    count = serializers.IntegerField()
    percentage = serializers.FloatField()


class ProjectMemberCountSerializer(serializers.Serializer):
    project_id = serializers.UUIDField()
    project_slug = serializers.SlugField()
    project_title = serializers.CharField()
    member_count = serializers.IntegerField()
    active_member_count = serializers.IntegerField()


class AssignmentWorkloadSerializer(serializers.Serializer):
    user_id = serializers.UUIDField(allow_null=True)
    email = serializers.EmailField(allow_null=True)
    full_name = serializers.CharField(allow_null=True)
    total_tasks = serializers.IntegerField()
    active_tasks = serializers.IntegerField()
    completed_tasks = serializers.IntegerField()
    overdue_tasks = serializers.IntegerField()


class RecentActivitySerializer(serializers.Serializer):
    total = serializers.IntegerField()
    project_events = serializers.IntegerField()
    task_events = serializers.IntegerField()


class ProjectIdentitySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    slug = serializers.SlugField()
    status = serializers.CharField()
    priority = serializers.CharField()


class DashboardMetricsSerializer(serializers.Serializer):
    """
    Chart-ready dashboard analytics for projects and tasks visible to a user.
    """
    date_range = AnalyticsDateRangeSerializer()

    total_projects = serializers.IntegerField()
    active_projects = serializers.IntegerField()
    completed_projects = serializers.IntegerField()
    total_project_members = serializers.IntegerField()
    project_member_counts = ProjectMemberCountSerializer(many=True)

    total_tasks = serializers.IntegerField()
    active_tasks = serializers.IntegerField()
    pending_tasks = serializers.IntegerField()
    completed_tasks = serializers.IntegerField()
    overdue_tasks = serializers.IntegerField()
    archived_tasks = serializers.IntegerField()
    task_completion_percentage = serializers.FloatField()

    tasks_by_status = ChartBucketSerializer(many=True)
    tasks_by_priority = ChartBucketSerializer(many=True)
    assignment_workload = AssignmentWorkloadSerializer(many=True)

    recent_activity_count = serializers.IntegerField()
    recent_activity = RecentActivitySerializer()

    total_revenue = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
    )
    unpaid_revenue = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
    )


class ProjectSummarySerializer(serializers.Serializer):
    """
    Project-scoped analytics for a single authorized project.
    """
    project = ProjectIdentitySerializer()
    date_range = AnalyticsDateRangeSerializer()

    total_tasks = serializers.IntegerField()
    active_tasks = serializers.IntegerField()
    completed_tasks = serializers.IntegerField()
    overdue_tasks = serializers.IntegerField()
    archived_tasks = serializers.IntegerField()
    active_members = serializers.IntegerField()
    task_completion_percentage = serializers.FloatField()

    tasks_by_status = ChartBucketSerializer(many=True)
    tasks_by_priority = ChartBucketSerializer(many=True)
    assignment_workload = AssignmentWorkloadSerializer(many=True)

    recent_activity_count = serializers.IntegerField()
    recent_activity = RecentActivitySerializer()


# Backward-compatible alias for older imports in the analytics app/tests.
SystemMetricsSerializer = DashboardMetricsSerializer
