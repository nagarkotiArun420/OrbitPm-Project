from django.http import Http404
from rest_framework import permissions
from rest_framework.views import APIView

from analytics.selectors import get_project_for_analytics
from analytics.services import get_dashboard_metrics, get_project_summary
from analytics.serializers import (
    AnalyticsDateRangeQuerySerializer,
    DashboardMetricsSerializer,
    ProjectSummarySerializer,
)
from analytics.permissions import CanAccessAnalytics
from common.responses import success_response


class DashboardOverviewMetricsView(APIView):
    """
    Endpoint serving dashboard KPI statistics and chart-ready task analytics.
    """
    permission_classes = [permissions.IsAuthenticated, CanAccessAnalytics]

    def get(self, request):
        query_serializer = AnalyticsDateRangeQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)

        metrics = get_dashboard_metrics(
            request.user,
            date_range=query_serializer.validated_data,
        )
        serializer = DashboardMetricsSerializer(metrics)
        return success_response(
            data=serializer.data,
            message='Dashboard analytics compiled successfully',
        )


class ProjectSummaryMetricsView(APIView):
    """
    Endpoint serving project-specific workflow and task analytics.
    """
    permission_classes = [permissions.IsAuthenticated, CanAccessAnalytics]

    def get(self, request, slug):
        query_serializer = AnalyticsDateRangeQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)

        project = get_project_for_analytics(request.user, slug)
        if project is None:
            raise Http404("Project not found.")

        summary = get_project_summary(
            project=project,
            user=request.user,
            date_range=query_serializer.validated_data,
        )
        serializer = ProjectSummarySerializer(summary)
        return success_response(
            data=serializer.data,
            message='Project analytics compiled successfully',
        )
