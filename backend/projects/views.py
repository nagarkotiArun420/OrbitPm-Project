from rest_framework import viewsets, permissions, filters, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import get_user_model
from projects.permissions import IsAdmin, IsProjectManager, IsAssignedDeveloper, IsProjectClient, IsMemberManagerOrReadOnly
from projects.selectors import get_authorized_projects
from projects.serializers import (
    ProjectListSerializer,
    ProjectDetailSerializer,
    ProjectCreateSerializer,
    ProjectUpdateSerializer,
    ProjectMemberSerializer
)
from projects.services import (
    create_project, update_project, delete_project,
    add_project_member, update_member_role, remove_project_member
)
from projects.models import ProjectMember

User = get_user_model()

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
        return get_authorized_projects(self.request.user, action=self.action)

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
            request=self.request,
            **serializer.validated_data
        )

    def perform_update(self, serializer):
        """
        Intercept DRF update pipeline and route updates to transactional services.
        """
        serializer.instance = update_project(
            project=self.get_object(), 
            request=self.request,
            **serializer.validated_data
        )

    def perform_destroy(self, instance):
        """
        Intercept DRF destroy pipeline and route deletions to transactional services.
        """
        delete_project(project=instance, request=self.request)


class ProjectMemberViewSet(viewsets.ModelViewSet):
    """
    ViewSet managing project team membership as a nested resource under projects.
    Scopes all operations to the parent project identified by project_slug.
    Delegates writes to transactional service functions for consistency.
    """
    serializer_class = ProjectMemberSerializer
    permission_classes = [permissions.IsAuthenticated, IsMemberManagerOrReadOnly]
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_project(self):
        """
        Resolve the parent project from the URL slug.
        Ensures the requesting user has visibility into this project.
        """
        return get_object_or_404(
            get_authorized_projects(self.request.user, action='detail'),
            slug=self.kwargs['project_slug']
        )

    def get_queryset(self):
        """
        Return members scoped to the parent project with optimized joins.
        """
        return ProjectMember.objects.filter(
            project__slug=self.kwargs['project_slug']
        ).select_related('user', 'invited_by')

    def get_serializer_context(self):
        """
        Inject the parent project into the serializer context for validation.
        """
        context = super().get_serializer_context()
        if self.kwargs.get('project_slug'):
            context['project'] = self.get_project()
        return context

    def create(self, request, *args, **kwargs):
        """
        Add a new member to the project via the service layer.
        """
        project = self.get_project()

        # Check object-level permission for the project
        self.check_object_permissions(request, project)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = get_object_or_404(User, id=serializer.validated_data['user_id'])
        role = serializer.validated_data.get('role', 'DEVELOPER')

        member = add_project_member(
            project=project,
            user=user,
            role=role,
            invited_by=request.user,
            request=request
        )

        output_serializer = ProjectMemberSerializer(member)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        """
        Update a member's role via the service layer.
        """
        member = self.get_object()
        self.check_object_permissions(request, member)

        new_role = request.data.get('role')
        if not new_role:
            return Response(
                {'role': ['This field is required.']},
                status=status.HTTP_400_BAD_REQUEST
            )

        from projects.constants import ProjectMemberRole
        valid_roles = [choice[0] for choice in ProjectMemberRole.choices]
        if new_role not in valid_roles:
            return Response(
                {'role': [f"Invalid role. Choose from: {', '.join(valid_roles)}"]},
                status=status.HTTP_400_BAD_REQUEST
            )

        member = update_member_role(
            member=member,
            new_role=new_role,
            updated_by=request.user,
            request=request
        )

        serializer = ProjectMemberSerializer(member)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """
        Remove a member from the project via the service layer.
        """
        member = self.get_object()
        self.check_object_permissions(request, member)

        remove_project_member(
            member=member,
            removed_by=request.user,
            request=request
        )

        return Response(status=status.HTTP_204_NO_CONTENT)
