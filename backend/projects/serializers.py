from rest_framework import serializers
from projects.models import Project, ProjectInvitation
from projects.constants import ProjectMemberRole
from accounts.serializers import UserMinSerializer
from django.contrib.auth import get_user_model

User = get_user_model()

class ProjectListSerializer(serializers.ModelSerializer):
    """
    Serializer optimized for listing projects.
    Exposes key metadata along with light nested manager details.
    """
    manager = UserMinSerializer(read_only=True)

    class Meta:
        model = Project
        fields = ('id', 'title', 'slug', 'status', 'priority', 'deadline', 'manager', 'created_at')
        read_only_fields = fields


class ProjectDetailSerializer(serializers.ModelSerializer):
    """
    Serializer providing a complete detailed overview of a project.
    Expands all relational foreign key user profiles using UserMinSerializer.
    """
    manager = UserMinSerializer(read_only=True)
    client = UserMinSerializer(read_only=True)
    created_by = UserMinSerializer(read_only=True)
    team_members = UserMinSerializer(many=True, read_only=True)

    class Meta:
        model = Project
        fields = (
            'id', 'title', 'slug', 'description', 'status', 'priority',
            'start_date', 'deadline', 'completed_at', 'budget',
            'client', 'manager', 'team_members', 'created_by',
            'created_at', 'updated_at'
        )
        read_only_fields = fields


class ProjectCreateSerializer(serializers.ModelSerializer):
    """
    Writable serializer for creating new projects with rich API-level validation boundaries.
    """
    class Meta:
        model = Project
        fields = (
            'title', 'description', 'status', 'priority',
            'start_date', 'deadline', 'budget',
            'client', 'manager', 'team_members'
        )

    def validate_title(self, value):
        # Case-insensitive title uniqueness check across active projects
        queryset = Project.objects.filter(title__iexact=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("A project with this title already exists.")
        return value

    def validate_budget(self, value):
        # Prevent API-level assignment of negative budgets
        if value is not None and value < 0:
            raise serializers.ValidationError("Budget cannot be a negative value.")
        return value

    def validate_manager(self, value):
        # Ensure user exists and possesses a managerial or admin role
        if value and value.role not in [User.Roles.MANAGER, User.Roles.ADMIN]:
            raise serializers.ValidationError("The assigned manager must have the ADMIN or MANAGER role.")
        return value

    def validate_client(self, value):
        # Ensure user exists and possesses a client role
        if value and value.role != User.Roles.CLIENT:
            raise serializers.ValidationError("The assigned client must have the CLIENT role.")
        return value

    def validate(self, attrs):
        start_date = attrs.get('start_date')
        deadline = attrs.get('deadline')
        
        # Verify deadline is equal to or after start_date
        if start_date and deadline and deadline < start_date:
            raise serializers.ValidationError({
                "deadline": "The project deadline cannot be before the start date."
            })
        return attrs


class ProjectUpdateSerializer(ProjectCreateSerializer):
    """
    Writable serializer for updating existing projects.
    Enforces identical validation rules as creation, with support for PATCH requests.
    """
    def validate(self, attrs):
        # Perform boundary validations taking partial updates (PATCH) into account
        start_date = attrs.get('start_date') if 'start_date' in attrs else (self.instance.start_date if self.instance else None)
        deadline = attrs.get('deadline') if 'deadline' in attrs else (self.instance.deadline if self.instance else None)
        
        if start_date and deadline and deadline < start_date:
            raise serializers.ValidationError({
                "deadline": "The project deadline cannot be before the start date."
            })
        return attrs

# Legacy compatibility alias for initial scaffold views (will be fully refactored in views development)
ProjectSerializer = ProjectDetailSerializer


class ProjectMemberSerializer(serializers.ModelSerializer):
    """
    Serializer for ProjectMember model. Expands user and invited_by
    via UserMinSerializer for reads, and accepts user_id for writes.
    """
    user = UserMinSerializer(read_only=True)
    invited_by = UserMinSerializer(read_only=True)
    user_id = serializers.UUIDField(write_only=True, required=True)

    class Meta:
        from projects.models import ProjectMember
        model = ProjectMember
        fields = (
            'id', 'user', 'user_id', 'role', 'joined_at',
            'invited_by', 'is_active'
        )
        read_only_fields = ('id', 'joined_at', 'invited_by', 'is_active')

    def validate_user_id(self, value):
        try:
            user = User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User with this ID does not exist.")

        if not user.is_active:
            raise serializers.ValidationError("Inactive users cannot be added as project members.")

        return value

    def validate(self, attrs):
        from projects.models import ProjectMember
        user_id = attrs.get('user_id')
        project = self.context.get('project')

        if project and user_id:
            if ProjectMember.objects.filter(project=project, user_id=user_id).exists():
                raise serializers.ValidationError({
                    'user_id': 'This user is already a member of this project.'
                })

        return attrs


class ProjectInvitationSerializer(serializers.ModelSerializer):
    """
    Read serializer for project invitations with lightweight user/project context.
    """
    invited_user = UserMinSerializer(read_only=True)
    invited_by = UserMinSerializer(read_only=True)
    project_slug = serializers.CharField(source='project.slug', read_only=True)
    project_title = serializers.CharField(source='project.title', read_only=True)
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = ProjectInvitation
        fields = (
            'id', 'project_slug', 'project_title',
            'invited_user', 'invited_by',
            'role', 'status', 'token',
            'expires_at', 'accepted_at', 'created_at',
            'is_expired',
        )
        read_only_fields = fields


class ProjectInvitationCreateSerializer(serializers.Serializer):
    """
    Input serializer for inviting an existing user to a project.
    """
    invited_user_id = serializers.UUIDField()
    role = serializers.ChoiceField(
        choices=ProjectMemberRole.choices,
        default=ProjectMemberRole.DEVELOPER,
    )
    expires_at = serializers.DateTimeField(required=False)

    def validate_invited_user_id(self, value):
        try:
            user = User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User with this ID does not exist.")

        if not user.is_active:
            raise serializers.ValidationError("Inactive users cannot receive project invitations.")

        return value

    def validate_expires_at(self, value):
        from django.utils import timezone
        if value <= timezone.now():
            raise serializers.ValidationError("Invitation expiry must be in the future.")
        return value


class ProjectInvitationActionSerializer(serializers.Serializer):
    """
    Optional token payload for accept/decline actions.
    """
    token = serializers.CharField(required=False, allow_blank=False)
