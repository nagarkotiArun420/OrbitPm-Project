from django.urls import path
from analytics.views import DashboardOverviewMetricsView

urlpatterns = [
    path('dashboard/', DashboardOverviewMetricsView.as_view(), name='analytics_dashboard'),
]
