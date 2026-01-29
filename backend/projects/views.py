from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from rest_framework import viewsets, permissions, filters, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import get_user_model
from common.responses import success_response
from projects.permissions import (
    IsAdmin,
    IsProjectManager,
    IsAssignedDeveloper,
    IsProjectClient,
    IsInvitationManagerOrReadOnly,
    IsMemberManagerOrReadOnly,
)
from projects.selectors import get_authorized_projects
from projects.serializers import (
    ProjectListSerializer,
    ProjectDetailSerializer,
    ProjectCreateSerializer,
    ProjectUpdateSerializer,
    ProjectInvitationActionSerializer,
    ProjectInvitationCreateSerializer,
    ProjectInvitationSerializer,
    ProjectMemberSerializer,
)
from projects.services import (
    create_project, update_project, delete_project,
    accept_invitation,
    add_project_member,
    create_invitation,
    decline_invitation,
    remove_project_member,
    revoke_invitation,
    update_member_role,
)
from projects.models import ProjectInvitation, ProjectMember

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


class ProjectInvitationViewSet(viewsets.ModelViewSet):
    """
    Nested project invitation workflow API.
    Supports invite, list, accept, decline, and revoke flows.
    """
    serializer_class = ProjectInvitationSerializer
    permission_classes = [permissions.IsAuthenticated, IsInvitationManagerOrReadOnly]
    http_method_names = ['get', 'post', 'delete', 'head', 'options']

    def get_project(self):
        return get_object_or_404(
            get_authorized_projects(self.request.user, action='detail'),
            slug=self.kwargs['project_slug']
        )

    def get_queryset(self):
        base_queryset = ProjectInvitation.objects.filter(
            project__slug=self.kwargs['project_slug']
        ).select_related(
            'project',
            'invited_user',
            'invited_by',
        )

        authorized_projects = get_authorized_projects(self.request.user, action='detail')
        visibility_filter = Q(project__in=authorized_projects)

        if self.action in ('retrieve', 'accept', 'decline'):
            visibility_filter |= Q(invited_user=self.request.user)

        return base_queryset.filter(visibility_filter).distinct()

    def get_serializer_class(self):
        if self.action == 'create':
            return ProjectInvitationCreateSerializer
        if self.action in ('accept', 'decline'):
            return ProjectInvitationActionSerializer
        return ProjectInvitationSerializer

    def _validation_error_detail(self, exc):
        return exc.message_dict if hasattr(exc, 'message_dict') else exc.messages

    def create(self, request, *args, **kwargs):
        project = self.get_project()
        self.check_object_permissions(request, project)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        invited_user = get_object_or_404(
            User,
            id=serializer.validated_data['invited_user_id'],
        )
        try:
            invitation = create_invitation(
                project=project,
                invited_user=invited_user,
                role=serializer.validated_data.get('role'),
                expires_at=serializer.validated_data.get('expires_at'),
                invited_by=request.user,
                request=request,
            )
        except DjangoValidationError as exc:
            raise ValidationError(self._validation_error_detail(exc))

        return success_response(
            data=ProjectInvitationSerializer(invitation).data,
            message='Project invitation created successfully',
            status_code=status.HTTP_201_CREATED,
        )

    def accept(self, request, *args, **kwargs):
        invitation = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            invitation = accept_invitation(
                invitation=invitation,
                actor=request.user,
                token=serializer.validated_data.get('token'),
                request=request,
            )
        except DjangoValidationError as exc:
            raise ValidationError(self._validation_error_detail(exc))

        return success_response(
            data=ProjectInvitationSerializer(invitation).data,
            message='Project invitation accepted successfully',
        )

    def decline(self, request, *args, **kwargs):
        invitation = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            invitation = decline_invitation(
                invitation=invitation,
                actor=request.user,
                token=serializer.validated_data.get('token'),
                request=request,
            )
        except DjangoValidationError as exc:
            raise ValidationError(self._validation_error_detail(exc))

        return success_response(
            data=ProjectInvitationSerializer(invitation).data,
            message='Project invitation declined successfully',
        )

    def revoke(self, request, *args, **kwargs):
        invitation = self.get_object()
        try:
            invitation = revoke_invitation(
                invitation=invitation,
                actor=request.user,
                request=request,
            )
        except DjangoValidationError as exc:
            raise ValidationError(self._validation_error_detail(exc))

        return success_response(
            data=ProjectInvitationSerializer(invitation).data,
            message='Project invitation revoked successfully',
        )

    def destroy(self, request, *args, **kwargs):
        invitation = self.get_object()
        try:
            invitation = revoke_invitation(
                invitation=invitation,
                actor=request.user,
                request=request,
            )
        except DjangoValidationError as exc:
            raise ValidationError(self._validation_error_detail(exc))

        return success_response(
            data=ProjectInvitationSerializer(invitation).data,
            message='Project invitation revoked successfully',
        )
