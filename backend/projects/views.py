from rest_framework import viewsets, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from projects.permissions import IsAdmin, IsProjectManager, IsAssignedDeveloper, IsProjectClient
from projects.selectors import get_authorized_projects
from projects.serializers import (
    ProjectListSerializer,
    ProjectDetailSerializer,
    ProjectCreateSerializer,
    ProjectUpdateSerializer
)
from projects.services import create_project, update_project, delete_project

class ProjectViewSet(viewsets.ModelViewSet):
    """
    Unified ViewSet managing full CRUD lifecycles for Projects.
    Funnels writes to transactional services and isolates reads per role permissions.
    """
    lookup_field = 'slug'
    permission_classes = [
        permissions.IsAuthenticated,
        (IsAdmin | IsProjectManager | IsAssignedDeveloper | IsProjectClient)
    ]
    
    # Filter and search backends configuration
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    filterset_fields = ('status', 'priority', 'manager')
    search_fields = ('title',)
    ordering_fields = ('created_at', 'deadline', 'budget', 'priority')
    ordering = ('-created_at',)

    def get_queryset(self):
        """
        Dynamically filter project listings to enforce strict data isolation per role.
        Utilizes selectors layer to enforce role-specific visibility and optimize queries.
        """
        return get_authorized_projects(self.request.user)

    def get_serializer_class(self):
        """
        Dynamically map serializer schemas depending on incoming action requests.
        """
        if self.action == 'list':
            return ProjectListSerializer
        elif self.action == 'retrieve':
            return ProjectDetailSerializer
        elif self.action == 'create':
            return ProjectCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ProjectUpdateSerializer
            
        return ProjectDetailSerializer

    def perform_create(self, serializer):
        """
        Intercept DRF save pipeline and route creation to transactional services.
        """
        serializer.instance = create_project(
            created_by=self.request.user, 
            **serializer.validated_data
        )

    def perform_update(self, serializer):
        """
        Intercept DRF update pipeline and route updates to transactional services.
        """
        serializer.instance = update_project(
            project=self.get_object(), 
            **serializer.validated_data
        )

    def perform_destroy(self, instance):
        """
        Intercept DRF destroy pipeline and route deletions to transactional services.
        """
        delete_project(project=instance)

