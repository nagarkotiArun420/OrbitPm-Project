from django.urls import path
from analytics.views import DashboardOverviewMetricsView, ProjectSummaryMetricsView

urlpatterns = [
    path('dashboard/', DashboardOverviewMetricsView.as_view(), name='analytics_dashboard'),
    path(
        'projects/<slug:slug>/summary/',
        ProjectSummaryMetricsView.as_view(),
        name='analytics_project_summary',
    ),
]
