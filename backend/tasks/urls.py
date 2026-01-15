from django.urls import path, include
from rest_framework.routers import DefaultRouter
from tasks.views import TaskViewSet, TaskCommentViewSet, TaskAttachmentViewSet

router = DefaultRouter()
router.register('', TaskViewSet, basename='task')

comment_list = TaskCommentViewSet.as_view({
    'get': 'list',
    'post': 'create'
})
comment_detail = TaskCommentViewSet.as_view({
    'get': 'retrieve',
    'patch': 'partial_update',
    'delete': 'destroy'
})

attachment_list = TaskAttachmentViewSet.as_view({
    'get': 'list',
    'post': 'create'
})
attachment_detail = TaskAttachmentViewSet.as_view({
    'delete': 'destroy'
})

urlpatterns = [
    path('<slug:task_slug>/comments/', comment_list, name='task-comment-list'),
    path('<slug:task_slug>/comments/<uuid:pk>/', comment_detail, name='task-comment-detail'),
    path('<slug:task_slug>/attachments/', attachment_list, name='task-attachment-list'),
    path('<slug:task_slug>/attachments/<uuid:pk>/', attachment_detail, name='task-attachment-detail'),
    path('', include(router.urls)),
]