from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from common.responses import success_response
from tasks.filters import TaskFilter
from tasks.models import Task, TaskAttachment, TaskComment
from tasks.permissions import (
    HasTaskAttachmentPermission,
    HasTaskCommentPermission,
    HasTaskPermission,
)
from tasks.selectors import get_authorized_tasks
from tasks.serializers import (
    TaskAttachmentSerializer,
    TaskCommentSerializer,
    TaskCreateSerializer,
    TaskDetailSerializer,
    TaskListSerializer,
    TaskUpdateSerializer,
)
from tasks.services import (
    archive_task,
    create_attachment,
    create_comment,
    create_task,
    delete_attachment,
    delete_comment,
    delete_task,
    restore_task,
    unarchive_task,
    update_comment,
    update_task,
)


class TaskViewSet(viewsets.ModelViewSet):
    """
    ViewSet for task CRUD, lifecycle actions, and deadline-aware filtering.
    """
    lookup_field = 'slug'
    permission_classes = [permissions.IsAuthenticated, HasTaskPermission]
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    filterset_class = TaskFilter
    search_fields = ('title', 'description', 'project__title')
    ordering_fields = ('created_at', 'updated_at', 'due_date', 'priority', 'status')
    ordering = ('-created_at',)

    def get_queryset(self):
        queryset = get_authorized_tasks(self.request.user, action=self.action)

        if self.action == 'restore':
            return queryset.order_by('-created_at')

        if self.action == 'list':
            if 'is_archived' in self.request.query_params:
                return queryset.filter(is_deleted=False).order_by('-created_at')
            return queryset.active().order_by('-created_at')

        return queryset.filter(is_deleted=False).order_by('-created_at')

    def get_serializer_class(self):
        if self.action == 'list':
            return TaskListSerializer
        if self.action == 'create':
            return TaskCreateSerializer
        if self.action in ('update', 'partial_update'):
            return TaskUpdateSerializer
        return TaskDetailSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            task = create_task(
                created_by=request.user,
                request=request,
                **serializer.validated_data
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.message_dict if hasattr(exc, 'message_dict') else exc.messages)

        return success_response(
            data=TaskDetailSerializer(task, context=self.get_serializer_context()).data,
            message='Task created successfully',
            status_code=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        task = self.get_object()
        serializer = self.get_serializer(task, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        try:
            task = update_task(task, request=request, **serializer.validated_data)
        except DjangoValidationError as exc:
            raise ValidationError(exc.message_dict if hasattr(exc, 'message_dict') else exc.messages)
        return success_response(
            data=TaskDetailSerializer(task, context=self.get_serializer_context()).data,
            message='Task updated successfully'
        )

    def destroy(self, request, *args, **kwargs):
        task = self.get_object()
        try:
            delete_task(task, request=request)
        except DjangoValidationError as exc:
            raise ValidationError(exc.message_dict if hasattr(exc, 'message_dict') else exc.messages)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def archive(self, request, slug=None):
        try:
            task = archive_task(self.get_object(), request=request)
        except DjangoValidationError as exc:
            raise ValidationError(exc.message_dict if hasattr(exc, 'message_dict') else exc.messages)
        return success_response(
            data=TaskDetailSerializer(task, context=self.get_serializer_context()).data,
            message='Task archived successfully'
        )

    @action(detail=True, methods=['post'])
    def restore(self, request, slug=None):
        try:
            task = restore_task(self.get_object(), request=request)
        except DjangoValidationError as exc:
            raise PermissionDenied(str(exc))
        return success_response(
            data=TaskDetailSerializer(task, context=self.get_serializer_context()).data,
            message='Task restored successfully'
        )

    @action(detail=True, methods=['post'])
    def unarchive(self, request, slug=None):
        try:
            task = unarchive_task(self.get_object(), request=request)
        except DjangoValidationError as exc:
            raise ValidationError(exc.message_dict if hasattr(exc, 'message_dict') else exc.messages)
        return success_response(
            data=TaskDetailSerializer(task, context=self.get_serializer_context()).data,
            message='Task unarchived successfully'
        )


class TaskCommentViewSet(viewsets.ModelViewSet):
    """
    Nested task comment API.
    """
    serializer_class = TaskCommentSerializer
    permission_classes = [permissions.IsAuthenticated, HasTaskCommentPermission]

    def get_task(self):
        return get_object_or_404(
            get_authorized_tasks(self.request.user, action='detail').active(),
            slug=self.kwargs['task_slug']
        )

    def get_queryset(self):
        if self.action != 'list':
            return TaskComment.objects.filter(
                task__slug=self.kwargs['task_slug']
            ).select_related('author', 'task__project__manager', 'task__project__created_by')
        return TaskComment.objects.active().filter(
            task__slug=self.kwargs['task_slug']
        ).select_related('author')

    def create(self, request, *args, **kwargs):
        task = self.get_task()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            comment = create_comment(
                task=task,
                author=request.user,
                content=serializer.validated_data['content'],
                request=request
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.message_dict if hasattr(exc, 'message_dict') else exc.messages)
        return success_response(
            data=self.get_serializer(comment).data,
            message='Comment created successfully',
            status_code=status.HTTP_201_CREATED
        )

    def partial_update(self, request, *args, **kwargs):
        comment = self.get_object()
        serializer = self.get_serializer(comment, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            comment = update_comment(
                comment=comment,
                editor=request.user,
                content=serializer.validated_data.get('content', comment.content),
                request=request
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.message_dict if hasattr(exc, 'message_dict') else exc.messages)
        return success_response(
            data=self.get_serializer(comment).data,
            message='Comment updated successfully'
        )

    def destroy(self, request, *args, **kwargs):
        try:
            delete_comment(self.get_object(), actor=request.user, request=request)
        except DjangoValidationError as exc:
            raise ValidationError(exc.message_dict if hasattr(exc, 'message_dict') else exc.messages)
        return Response(status=status.HTTP_204_NO_CONTENT)


class TaskAttachmentViewSet(viewsets.ModelViewSet):
    """
    Nested task attachment API.
    """
    serializer_class = TaskAttachmentSerializer
    permission_classes = [permissions.IsAuthenticated, HasTaskAttachmentPermission]
    http_method_names = ['get', 'post', 'delete', 'head', 'options']

    def get_task(self):
        return get_object_or_404(
            get_authorized_tasks(self.request.user, action='detail').filter(is_deleted=False),
            slug=self.kwargs['task_slug']
        )

    def get_queryset(self):
        if self.action != 'list':
            return TaskAttachment.objects.filter(
                task__slug=self.kwargs['task_slug']
            ).select_related('task__project__manager', 'task__project__created_by', 'uploaded_by')
        return TaskAttachment.objects.filter(
            task__slug=self.kwargs['task_slug']
        ).select_related('uploaded_by')

    def create(self, request, *args, **kwargs):
        task = self.get_task()
        upload = request.FILES.get('file')
        if upload is None:
            raise ValidationError({'file': ['A file is required.']})

        try:
            attachment = create_attachment(
                task=task,
                uploaded_by=request.user,
                file=upload,
                request=request
            )
        except DjangoValidationError as exc:
            raise ValidationError({'file': exc.messages})
        return success_response(
            data=self.get_serializer(attachment).data,
            message='Attachment uploaded successfully',
            status_code=status.HTTP_201_CREATED
        )

    def destroy(self, request, *args, **kwargs):
        try:
            delete_attachment(self.get_object(), actor=request.user, request=request)
        except DjangoValidationError as exc:
            raise ValidationError(exc.message_dict if hasattr(exc, 'message_dict') else exc.messages)
        return Response(status=status.HTTP_204_NO_CONTENT)
