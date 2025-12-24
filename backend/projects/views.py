from rest_framework import viewsets, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from accounts.models import User
from projects.models import Project
from projects.permissions import HasProjectPermission
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
    permission_classes = [permissions.IsAuthenticated, HasProjectPermission]
    
    # Filter and search backends configuration
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    filterset_fields = ('status', 'priority', 'manager')
    search_fields = ('title',)
    ordering_fields = ('created_at', 'deadline', 'budget', 'priority')
    ordering = ('-created_at',)

    def get_queryset(self):
        """
        Dynamically filter project listings to enforce strict data isolation per role:
        - ADMIN: Full access to all projects.
        - MANAGER: Associated projects (manager, creator, client, or team member).
        - DEVELOPER: Projects where they are in team members.
        - CLIENT: Projects where they are the designated client.
        
        Leverages select_related and prefetch_related to eliminate N+1 queries.
        """
        user = self.request.user
        
        # Base query optimization
        queryset = Project.objects.all().select_related(
            'manager', 'client', 'created_by'
        ).prefetch_related('team_members')

        # ADMIN possesses omniscient view
        if user.role == User.Roles.ADMIN:
            return queryset

        # MANAGER sees any projects they manage, created, or are mapped onto
        if user.role == User.Roles.MANAGER:
            return queryset.filter(
                Q(manager=user) | 
                Q(created_by=user) | 
                Q(client=user) | 
                Q(team_members=user)
            ).distinct()

        # DEVELOPER sees projects they actively program on
        if user.role == User.Roles.DEVELOPER:
            return queryset.filter(team_members=user)

        # CLIENT sees projects they are funding
        if user.role == User.Roles.CLIENT:
            return queryset.filter(client=user)

        return Project.objects.none()

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
