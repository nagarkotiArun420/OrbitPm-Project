from rest_framework import serializers

class SystemMetricsSerializer(serializers.Serializer):
    """
    Serializer representing aggregated SaaS operational statistics.
    Used for dashboard widget loads.
    """
    total_projects = serializers.IntegerField()
    active_projects = serializers.IntegerField()
    completed_projects = serializers.IntegerField()
    total_tasks = serializers.IntegerField()
    pending_tasks = serializers.IntegerField()
    completed_tasks = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    unpaid_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
