from django.urls import path, include
from rest_framework.routers import DefaultRouter
from projects.views import ProjectInvitationViewSet, ProjectViewSet, ProjectMemberViewSet

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
    path(
        '<slug:project_slug>/invitations/',
        ProjectInvitationViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='project-invitation-list'
    ),
    path(
        '<slug:project_slug>/invitations/<uuid:pk>/',
        ProjectInvitationViewSet.as_view({'get': 'retrieve', 'delete': 'destroy'}),
        name='project-invitation-detail'
    ),
    path(
        '<slug:project_slug>/invitations/<uuid:pk>/accept/',
        ProjectInvitationViewSet.as_view({'post': 'accept'}),
        name='project-invitation-accept'
    ),
    path(
        '<slug:project_slug>/invitations/<uuid:pk>/decline/',
        ProjectInvitationViewSet.as_view({'post': 'decline'}),
        name='project-invitation-decline'
    ),
    path(
        '<slug:project_slug>/invitations/<uuid:pk>/revoke/',
        ProjectInvitationViewSet.as_view({'post': 'revoke'}),
        name='project-invitation-revoke'
    ),
]
