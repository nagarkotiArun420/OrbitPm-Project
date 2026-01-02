from rest_framework import viewsets, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from tasks.permissions import HasTaskPermission
from tasks.selectors import get_authorized_tasks
from tasks.serializers import (
    TaskListSerializer,
    TaskDetailSerializer,
    TaskCreateSerializer,
    TaskUpdateSerializer,
)
from tasks.services import create_task, update_task, delete_task


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
    filterset_fields = ('status', 'priority', 'assigned_to', 'project')
    search_fields = ('title',)
    ordering_fields = ('created_at', 'due_date', 'priority', 'status')
    ordering = ('-created_at',)

    def get_queryset(self):
        """
        Dynamically filter task listings to enforce strict data isolation per role.
        Utilizes selectors layer to enforce role-specific visibility and optimize queries.
        """
        return get_authorized_tasks(self.request.user)

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

