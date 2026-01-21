from django.urls import path, include
from rest_framework.routers import DefaultRouter
from projects.views import ProjectViewSet, ProjectMemberViewSet

router = DefaultRouter()
router.register('', ProjectViewSet, basename='project')

urlpatterns = [
    path('', include(router.urls)),
    path(
        '<slug:project_slug>/members/',
        ProjectMemberViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='project-member-list'
    ),
    path(
        '<slug:project_slug>/members/<uuid:pk>/',
        ProjectMemberViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update', 'delete': 'destroy'}),
        name='project-member-detail'
    ),
]
