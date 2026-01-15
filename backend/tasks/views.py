from rest_framework import viewsets, permissions, filters, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend
from tasks.filters import TaskFilter
from tasks.permissions import HasTaskPermission, HasTaskCommentPermission, HasTaskAttachmentPermission
from tasks.selectors import get_authorized_tasks
from tasks.serializers import (
    TaskListSerializer,
    TaskDetailSerializer,
    TaskCreateSerializer,
    TaskUpdateSerializer,
    TaskCommentSerializer,
    TaskAttachmentSerializer,
)
from tasks.services import (
    create_task,
    update_task,
    delete_task,
    restore_task,
    archive_task,
    unarchive_task,
    create_comment,
    update_comment,
    delete_comment,
    create_attachment,
    delete_attachment,
)
from tasks.models import TaskComment, TaskAttachment


class TaskViewSet(viewsets.ModelViewSet):
    """
    Unified ViewSet managing full CRUD lifecycles for Tasks.
    Funnels writes to transactional services and isolates reads per role permissions.

    Endpoints:
        GET    /api/v1/tasks/          — List authorized tasks (paginated, filterable)
        POST   /api/v1/tasks/          — Create a new task
        GET    /api/v1/tasks/{slug}/   — Retrieve task details
        PATCH  /api/v1/tasks/{slug}/   — Partially update a task
        DELETE /api/v1/tasks/{slug}/   — Delete a task
    """
    lookup_field = 'slug'
    permission_classes = [permissions.IsAuthenticated, HasTaskPermission]

    # Filter, search, and ordering backends
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    filterset_class = TaskFilter
    search_fields = ('title', 'description', 'project__title')
    ordering_fields = ('created_at', 'due_date', 'priority', 'status', 'updated_at')
    ordering = ('-created_at',)

    def get_queryset(self):
        """
        Dynamically filter task listings to enforce strict data isolation per role.
        Utilizes selectors layer to enforce role-specific visibility and optimize queries.
        Excludes soft-deleted tasks, and partitions archived/active tasks in lists.
        """
        qs = get_authorized_tasks(self.request.user).filter(is_deleted=False)
        if self.action == 'list':
            is_archived = self.request.query_params.get('is_archived', 'false').lower() == 'true'
            qs = qs.filter(is_archived=is_archived)
        return qs

    def get_serializer_class(self):
        """
        Dynamically map serializer schemas depending on incoming action requests.
        """
        if self.action == 'list':
            return TaskListSerializer
        elif self.action == 'retrieve':
            return TaskDetailSerializer
        elif self.action == 'create':
            return TaskCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return TaskUpdateSerializer

        return TaskDetailSerializer

    def get_object(self):
        """
        Custom get_object lookup to fetch soft-deleted or archived tasks
        when executing recovery operations.
        """
        if self.action in ['restore', 'unarchive']:
            queryset = get_authorized_tasks(self.request.user)
            lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
            filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
            obj = get_object_or_404(queryset, **filter_kwargs)
            self.check_object_permissions(self.request, obj)
            return obj
        return super().get_object()

    def perform_create(self, serializer):
        """
        Intercept DRF save pipeline and route creation to transactional services.
        Tags the requesting user as the task creator (assigned_by).
        """
        serializer.instance = create_task(
            created_by=self.request.user,
            request=self.request,
            **serializer.validated_data
        )

    def perform_update(self, serializer):
        """
        Intercept DRF update pipeline and route updates to transactional services.
        """
        serializer.instance = update_task(
            task=self.get_object(),
            request=self.request,
            **serializer.validated_data
        )

    def perform_destroy(self, instance):
        """
        Intercept DRF destroy pipeline and route deletions to transactional services.
        """
        delete_task(task=instance, request=self.request)

    @action(detail=True, methods=['post'], url_path='restore')
    def restore(self, request, slug=None):
        """
        Restore a soft-deleted task.
        """
        task = self.get_object()
        try:
            restore_task(task=task, request=request)
            serializer = TaskDetailSerializer(task)
            return Response({
                'message': 'Task restored successfully.',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        except ValidationError as e:
            msg = e.message if hasattr(e, 'message') else (e.messages[0] if hasattr(e, 'messages') and e.messages else str(e))
            return Response({'error': msg}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='archive')
    def archive(self, request, slug=None):
        """
        Archive a completed task.
        """
        task = self.get_object()
        try:
            archive_task(task=task, request=request)
            serializer = TaskDetailSerializer(task)
            return Response({
                'message': 'Task archived successfully.',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        except ValidationError as e:
            msg = e.message if hasattr(e, 'message') else (e.messages[0] if hasattr(e, 'messages') and e.messages else str(e))
            return Response({'error': msg}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='unarchive')
    def unarchive(self, request, slug=None):
        """
        Unarchive an archived task.
        """
        task = self.get_object()
        try:
            unarchive_task(task=task, request=request)
            serializer = TaskDetailSerializer(task)
            return Response({
                'message': 'Task unarchived successfully.',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        except ValidationError as e:
            msg = e.message if hasattr(e, 'message') else (e.messages[0] if hasattr(e, 'messages') and e.messages else str(e))
            return Response({'error': msg}, status=status.HTTP_400_BAD_REQUEST)


class TaskCommentViewSet(viewsets.ModelViewSet):
    """
    ViewSet to manage comments on a Task.
    Supports GET (list), POST (create), PATCH (partial_update), and DELETE (destroy).
    Enforces role-based permissions and soft delete behaviors.
    """
    serializer_class = TaskCommentSerializer
    permission_classes = [permissions.IsAuthenticated, HasTaskCommentPermission]
    lookup_field = 'pk'

    def get_queryset(self):
        """
        Returns comments for the requested task, optimizing queries
        using select_related and prefetch_related.
        """
        task_slug = self.kwargs.get('task_slug')
        return TaskComment.objects.filter(
            task__slug=task_slug
        ).select_related(
            'author',
            'task',
            'task__project',
            'task__project__manager',
            'task__project__client',
        ).prefetch_related(
            'task__project__team_members',
        )

    def perform_create(self, serializer):
        """
        Create a task comment utilizing the service layer.
        """
        task_slug = self.kwargs.get('task_slug')
        from tasks.selectors import get_authorized_tasks
        from django.shortcuts import get_object_or_404
        task = get_object_or_404(get_authorized_tasks(self.request.user), slug=task_slug)

        serializer.instance = create_comment(
            task=task,
            author=self.request.user,
            content=serializer.validated_data.get('content'),
            request=self.request
        )

    def perform_update(self, serializer):
        """
        Update a task comment utilizing the service layer.
        """
        serializer.instance = update_comment(
            comment=self.get_object(),
            editor=self.request.user,
            content=serializer.validated_data.get('content'),
            request=self.request
        )

    def perform_destroy(self, instance):
        """
        Soft-delete a task comment utilizing the service layer.
        """
        delete_comment(
            comment=instance,
            actor=self.request.user,
            request=self.request
        )


class TaskAttachmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet to manage file attachments on a Task.
    Supports GET (list), POST (create), and DELETE (destroy).
    Enforces role-based permissions and optimal select_related/prefetch_related queries.
    """
    serializer_class = TaskAttachmentSerializer
    permission_classes = [permissions.IsAuthenticated, HasTaskAttachmentPermission]
    lookup_field = 'pk'

    def get_queryset(self):
        """
        Returns attachments for the requested task, optimizing queries
        using select_related to prevent N+1 DB lookups.
        """
        task_slug = self.kwargs.get('task_slug')
        return TaskAttachment.objects.filter(
            task__slug=task_slug
        ).select_related(
            'uploaded_by',
            'task',
            'task__project',
            'task__project__manager',
            'task__project__client',
        ).prefetch_related(
            'task__project__team_members',
        )

    def perform_create(self, serializer):
        """
        Uploads a new attachment for the task, intercepting Django ValidationErrors
        to return formatted DRF bad request responses.
        """
        task_slug = self.kwargs.get('task_slug')
        from tasks.selectors import get_authorized_tasks
        from django.shortcuts import get_object_or_404
        from django.core.exceptions import ValidationError as DjangoValidationError
        from rest_framework.exceptions import ValidationError as DRFValidationError

        task = get_object_or_404(get_authorized_tasks(self.request.user).filter(is_deleted=False), slug=task_slug)

        try:
            serializer.instance = create_attachment(
                task=task,
                uploaded_by=self.request.user,
                file=serializer.validated_data.get('file'),
                request=self.request
            )
        except DjangoValidationError as e:
            msg = e.message if hasattr(e, 'message') else (e.messages[0] if hasattr(e, 'messages') and e.messages else str(e))
            raise DRFValidationError({'file': [msg]})

    def perform_destroy(self, instance):
        """
        Deletes a task attachment, physically removing the file and deleting the DB record.
        """
        from django.core.exceptions import ValidationError as DjangoValidationError
        from rest_framework.exceptions import ValidationError as DRFValidationError

        try:
            delete_attachment(
                attachment=instance,
                actor=self.request.user,
                request=self.request
            )
        except DjangoValidationError as e:
            msg = e.message if hasattr(e, 'message') else (e.messages[0] if hasattr(e, 'messages') and e.messages else str(e))
            raise DRFValidationError({'error': msg})

