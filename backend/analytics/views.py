from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from analytics.services import calculate_dashboard_metrics
from analytics.serializers import SystemMetricsSerializer
from analytics.permissions import CanAccessAnalytics

class DashboardOverviewMetricsView(APIView):
    """
    Endpoint serving system-wide overview KPI statistics for dashboard cards.
    """
    permission_classes = [permissions.IsAuthenticated, CanAccessAnalytics]

    def get(self, request):
        metrics = calculate_dashboard_metrics(request.user)
        serializer = SystemMetricsSerializer(metrics)
        return Response({
            'success': True,
            'message': 'Dashboard analytics compiled successfully',
            'data': serializer.data,
            'error': None
        })
