from rest_framework import serializers
from django.contrib.auth import get_user_model
from tasks.models import Task, TaskComment, TaskAttachment, TaskLabel
from tasks.constants import TaskStatus
from tasks.validators import (
    ALLOWED_TRANSITIONS,
    validate_status_transition,
    validate_due_date_within_project,
    validate_assignee_project_membership,
    validate_task_assignment,
)
from accounts.serializers import UserMinSerializer

User = get_user_model()


# ──────────────────────────────────────────────────────────────
# Inline Nested Serializers
# ──────────────────────────────────────────────────────────────

class TaskProjectSerializer(serializers.Serializer):
    """
    Lightweight, read-only serializer for embedding project context
    inside task responses without exposing the full project payload.
    """
    id = serializers.UUIDField(read_only=True)
    title = serializers.CharField(read_only=True)
    slug = serializers.SlugField(read_only=True)
    status = serializers.CharField(read_only=True)


# ──────────────────────────────────────────────────────────────
# Read Serializers
# ──────────────────────────────────────────────────────────────

class TaskLabelInlineSerializer(serializers.ModelSerializer):
    """Lightweight label representation for embedding in task responses."""
    class Meta:
        model = TaskLabel
        fields = ('id', 'name', 'slug', 'color')
        read_only_fields = fields


class TaskListSerializer(serializers.ModelSerializer):
    """
    Serializer optimized for listing tasks.
    Exposes key metadata with lightweight nested assignee details.
    """
    assigned_to = UserMinSerializer(read_only=True)
    project_title = serializers.CharField(source='project.title', read_only=True)
    project_slug = serializers.CharField(source='project.slug', read_only=True)
    overdue_duration = serializers.DurationField(read_only=True)
    labels = TaskLabelInlineSerializer(many=True, read_only=True)

    class Meta:
        model = Task
        fields = (
            'id', 'title', 'slug', 'status', 'priority',
            'due_date', 'is_overdue', 'overdue_duration', 'assigned_to',
            'project_title', 'project_slug',
            'labels',
            'created_at', 'is_archived',
        )
        read_only_fields = fields


class TaskDetailSerializer(serializers.ModelSerializer):
    """
    Serializer providing a complete detailed overview of a task.
    Expands all relational foreign key user profiles and project context.
    """
    assigned_to = UserMinSerializer(read_only=True)
    assigned_by = UserMinSerializer(read_only=True)
    project = TaskProjectSerializer(read_only=True)
    overdue_duration = serializers.DurationField(read_only=True)
    labels = TaskLabelInlineSerializer(many=True, read_only=True)

    class Meta:
        model = Task
        fields = (
            'id', 'title', 'slug', 'description',
            'status', 'priority',
            'project', 'assigned_to', 'assigned_by',
            'estimated_hours', 'actual_hours',
            'due_date', 'is_overdue', 'overdue_duration', 'completed_at',
            'labels',
            'is_archived', 'archived_at',
            'created_at', 'updated_at',
        )
        read_only_fields = fields


# ──────────────────────────────────────────────────────────────
# Write Serializers
# ──────────────────────────────────────────────────────────────

class TaskCreateSerializer(serializers.ModelSerializer):
    """
    Writable serializer for creating new tasks with rich API-level
    validation boundaries for assignment, due dates, and hours.
    """
    class Meta:
        model = Task
        fields = (
            'title', 'description', 'project', 'assigned_to',
            'status', 'priority',
            'estimated_hours', 'actual_hours', 'due_date',
        )

    def validate_estimated_hours(self, value):
        """Prevent API-level assignment of negative estimated hours."""
        if value is not None and value < 0:
            raise serializers.ValidationError(
                "Estimated hours cannot be negative."
            )
        return value

    def validate_actual_hours(self, value):
        """Prevent API-level assignment of negative actual hours."""
        if value is not None and value < 0:
            raise serializers.ValidationError(
                "Actual hours cannot be negative."
            )
        return value

    def validate(self, attrs):
        """
        Cross-field validations:
        1. Due date must fall within project timeline bounds.
        2. Assigned user must be a member of the project team and satisfy assignment policies.
        """
        request = self.context.get('request')
        actor = request.user if request else None

        project = attrs.get('project')
        due_date = attrs.get('due_date')
        assigned_to = attrs.get('assigned_to')

        # Validate due date against project boundaries
        if due_date and project:
            try:
                validate_due_date_within_project(due_date, project)
            except Exception as e:
                raise serializers.ValidationError({'due_date': str(e)})

        # Validate assignee and assignment rules
        if 'assigned_to' in attrs or project:
            try:
                temp_task = Task(project=project, assigned_to=assigned_to)
                validate_task_assignment(temp_task, assigned_to, actor=actor)
            except Exception as e:
                raise serializers.ValidationError({'assigned_to': str(e)})

        return attrs


class TaskUpdateSerializer(TaskCreateSerializer):
    """
    Writable serializer for updating existing tasks.
    Enforces identical validation rules as creation, with additional
    status transition enforcement and PATCH-aware field resolution.
    """
    class Meta(TaskCreateSerializer.Meta):
        fields = TaskCreateSerializer.Meta.fields + ('is_archived',)

    def validate(self, attrs):
        """
        Extends creation validation with:
        1. Status transition enforcement via the agile workflow matrix.
        2. PATCH-aware field resolution (falls back to instance values).
        3. Strict task assignment policies.
        """
        request = self.context.get('request')
        actor = request.user if request else None

        # Resolve fields for partial updates (PATCH)
        project = attrs.get('project') if 'project' in attrs else (
            self.instance.project if self.instance else None
        )
        due_date = attrs.get('due_date') if 'due_date' in attrs else (
            self.instance.due_date if self.instance else None
        )
        assigned_to = attrs.get('assigned_to') if 'assigned_to' in attrs else (
            self.instance.assigned_to if self.instance else None
        )

        # Validate due date against project boundaries
        if due_date and project:
            try:
                validate_due_date_within_project(due_date, project)
            except Exception as e:
                raise serializers.ValidationError({'due_date': str(e)})

        # Validate assignee and task assignment rules
        if 'assigned_to' in attrs or 'project' in attrs:
            try:
                temp_status = attrs.get('status', self.instance.status if self.instance else TaskStatus.TODO)
                temp_task = Task(project=project, assigned_to=self.instance.assigned_to if self.instance else None, status=temp_status)
                if self.instance and self.instance.pk:
                    temp_task.pk = self.instance.pk
                validate_task_assignment(temp_task, assigned_to, actor=actor)
            except Exception as e:
                raise serializers.ValidationError({'assigned_to': str(e)})

        # Validate archiving permission and rules
        if attrs.get('is_archived') is True and self.instance and not self.instance.is_archived:
            # Check if task status is completed
            status_val = attrs.get('status', self.instance.status)
            if status_val != TaskStatus.COMPLETED:
                raise serializers.ValidationError({'is_archived': 'Only completed tasks can be archived.'})

            if not actor or actor.role not in [User.Roles.ADMIN, User.Roles.MANAGER]:
                raise serializers.ValidationError({'is_archived': 'Only admins and managers can archive tasks.'})
            if actor.role == User.Roles.MANAGER:
                is_manager_of_project = (
                    project.manager == actor or
                    project.created_by == actor
                )
                if not is_manager_of_project:
                    raise serializers.ValidationError({'is_archived': 'You can only archive tasks in your managed projects.'})

        # Validate status transition if status is being changed
        new_status = attrs.get('status')
        if new_status and self.instance and new_status != self.instance.status:
            try:
                validate_status_transition(self.instance.status, new_status)
            except Exception as e:
                raise serializers.ValidationError({'status': str(e)})

        return attrs


# Legacy compatibility alias
TaskSerializer = TaskDetailSerializer


class TaskCommentSerializer(serializers.ModelSerializer):
    author = UserMinSerializer(read_only=True)

    class Meta:
        model = TaskComment
        fields = [
            'id',
            'task',
            'author',
            'content',
            'is_edited',
            'edited_at',
            'is_deleted',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'task',
            'author',
            'is_edited',
            'edited_at',
            'is_deleted',
            'created_at',
            'updated_at',
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.is_deleted:
            data['content'] = "This comment was deleted."
        return data


class TaskAttachmentSerializer(serializers.ModelSerializer):
    uploaded_by = UserMinSerializer(read_only=True)

    class Meta:
        model = TaskAttachment
        fields = [
            'id',
            'task',
            'uploaded_by',
            'file',
            'original_filename',
            'file_size',
            'mime_type',
            'uploaded_at',
        ]
        read_only_fields = [
            'id',
            'task',
            'uploaded_by',
            'original_filename',
            'file_size',
            'mime_type',
            'uploaded_at',
        ]


# ──────────────────────────────────────────────────────────────
# Task Label Serializers
# ──────────────────────────────────────────────────────────────

class TaskLabelSerializer(serializers.ModelSerializer):
    """Full CRUD serializer for TaskLabel."""
    class Meta:
        model = TaskLabel
        fields = (
            'id', 'name', 'slug', 'color', 'description',
            'project', 'created_at',
        )
        read_only_fields = ('id', 'slug', 'created_at')

    def validate(self, attrs):
        project = attrs.get('project') or (self.instance.project if self.instance else None)
        name = attrs.get('name') or (self.instance.name if self.instance else None)
        if project and name:
            from django.utils.text import slugify
            slug = slugify(name)
            qs = TaskLabel.objects.filter(project=project, slug=slug)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {'name': f"A label with name '{name}' already exists in this project."}
                )
        return attrs


class TaskLabelUpdateSerializer(serializers.ModelSerializer):
    """Update serializer — project is immutable after creation."""
    class Meta:
        model = TaskLabel
        fields = ('name', 'color', 'description')

    def validate_name(self, value):
        if self.instance:
            from django.utils.text import slugify
            slug = slugify(value)
            if TaskLabel.objects.filter(
                project=self.instance.project, slug=slug
            ).exclude(pk=self.instance.pk).exists():
                raise serializers.ValidationError(
                    f"A label with name '{value}' already exists in this project."
                )
        return value


class TaskLabelAssignSerializer(serializers.Serializer):
    """Serializer for assigning/removing labels to/from a task."""
    label_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        help_text='List of label UUIDs to assign or remove.'
    )
