import uuid
from datetime import timedelta
from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.utils import timezone
from django.core.exceptions import ValidationError
from projects.models import Project
from tasks.constants import TaskStatus, TaskPriority
from tasks.validators import validate_hours_non_negative
from tasks.managers import TaskManager, TaskCommentManager


class Task(models.Model):
    """
    Task model representing granular units of work within a Project.
    Includes comprehensive workflow states, assignment constraints,
    estimations, and validation bounds.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField(blank=True, null=True)

    objects = TaskManager()
    
    status = models.CharField(
        max_length=20,
        choices=TaskStatus.choices,
        default=TaskStatus.TODO,
        db_index=True
    )
    priority = models.CharField(
        max_length=20,
        choices=TaskPriority.choices,
        default=TaskPriority.MEDIUM,
        db_index=True
    )
    
    # Relationships
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='tasks',
        db_index=True
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tasks',
        db_index=True
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_tasks'
    )
    
    # Work estimations & actual tracks
    estimated_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[validate_hours_non_negative]
    )
    actual_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[validate_hours_non_negative]
    )
    
    # Timeline
    due_date = models.DateField(blank=True, null=True, db_index=True)
    completed_at = models.DateTimeField(blank=True, null=True, db_index=True)
    
    # Soft delete fields
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(blank=True, null=True, db_index=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deleted_tasks'
    )
    
    # Archive fields
    is_archived = models.BooleanField(default=False, db_index=True)
    archived_at = models.DateTimeField(blank=True, null=True, db_index=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(
                fields=['is_deleted', 'is_archived', 'status', 'due_date'],
                name='task_deadline_state_idx'
            ),
            models.Index(
                fields=['due_date', 'status'],
                name='task_due_status_idx'
            ),
        ]

    def __str__(self):
        return f"{self.title} ({self.status})"

    @property
    def is_overdue(self):
        """
        Indicates whether the task is active, incomplete, and past its due date.
        """
        return (
            self.due_date is not None and
            self.due_date < timezone.localdate() and
            self.status != TaskStatus.COMPLETED and
            not self.is_archived and
            not self.is_deleted
        )

    @property
    def overdue_duration(self):
        """
        Returns how long the task has been overdue, or zero for non-overdue tasks.
        """
        if not self.is_overdue:
            return timedelta(0)
        return timezone.localdate() - self.due_date

    def clean(self):
        super().clean()
        
        # 1. Validation for hours estimation
        if self.estimated_hours is not None and self.estimated_hours < 0:
            raise ValidationError({'estimated_hours': 'Estimated hours cannot be negative.'})
            
        if self.actual_hours is not None and self.actual_hours < 0:
            raise ValidationError({'actual_hours': 'Actual hours cannot be negative.'})

        # 2. Validation for task due date aligning with project timelines
        if self.due_date and self.project:
            if self.project.start_date and self.due_date < self.project.start_date:
                raise ValidationError({
                    'due_date': 'The task due date cannot be before the project start date.'
                })
            if self.project.deadline and self.due_date > self.project.deadline:
                raise ValidationError({
                    'due_date': 'The task due date cannot be after the project deadline.'
                })

        # 3. Validation that assigned user belongs to the project team
        if self.project and self.assigned_to:
            is_team_member = (
                self.project.team_members.filter(id=self.assigned_to.id).exists() or
                self.project.manager == self.assigned_to or
                self.project.created_by == self.assigned_to
            )
            if not is_team_member:
                raise ValidationError({
                    'assigned_to': 'The assigned user must belong to the project team.'
                })

        # 4. Lifecycle logic: automatic completed_at adjustments
        if self.status == TaskStatus.COMPLETED:
            if not self.completed_at:
                self.completed_at = timezone.now()
        else:
            self.completed_at = None

        # 5. Soft Delete and Archive validations & adjustments
        if self.pk:
            try:
                original = Task._base_manager.get(pk=self.pk)
                if original.is_deleted and self.is_deleted:
                    raise ValidationError("Deleted tasks cannot be modified.")
                if original.is_archived and original.status != self.status:
                    raise ValidationError("Archived tasks cannot change workflow states.")
            except Task.DoesNotExist:
                pass

        if self.is_archived:
            if self.status != TaskStatus.COMPLETED:
                raise ValidationError("Only completed tasks can be archived.")
            if not self.archived_at:
                self.archived_at = timezone.now()
        else:
            self.archived_at = None

    def save(self, *args, **kwargs):
        # Auto-generate unique slug from title if empty
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while Task.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
            
        self.full_clean()
        super().save(*args, **kwargs)


class TaskComment(models.Model):
    """
    Model representing comments/discussion notes on a Task.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(
        'Task',
        on_delete=models.CASCADE,
        related_name='comments'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='task_comments'
    )
    content = models.TextField()
    is_edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TaskCommentManager()

    class Meta:
        ordering = ['created_at']

    def clean(self):
        super().clean()
        
        # Validation rules:
        # 1. Empty comments are invalid
        if not self.content or not self.content.strip():
            raise ValidationError("Comment content cannot be empty.")

        # 2. Deleted tasks cannot receive comments
        if self.task.is_deleted:
            raise ValidationError("Cannot add comments to a deleted task.")

        # 3. Archived tasks cannot receive new comments
        if self._state.adding and self.task.is_archived:
            raise ValidationError("Cannot add new comments to an archived task.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


def task_attachment_upload_path(instance, filename):
    import os
    import uuid
    from django.utils.text import get_valid_filename
    name, ext = os.path.splitext(filename)
    safe_name = get_valid_filename(name)[:100]
    unique_filename = f"{uuid.uuid4()}_{safe_name}{ext}"
    return f"tasks/{instance.task.id}/attachments/{unique_filename}"


class TaskAttachment(models.Model):
    """
    Model representing a file attachment uploaded to a Task.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(
        'Task',
        on_delete=models.CASCADE,
        related_name='attachments',
        db_index=True
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_attachments',
        db_index=True
    )
    file = models.FileField(upload_to=task_attachment_upload_path)
    original_filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()
    mime_type = models.CharField(max_length=100)
    uploaded_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.original_filename} (Task: {self.task.title})"

    def clean(self):
        super().clean()
        
        # 1. Deleted tasks cannot receive uploads
        if self.task.is_deleted:
            raise ValidationError("Cannot add attachments to a deleted task.")
            
        # 2. Archived tasks cannot receive uploads
        if self._state.adding and self.task.is_archived:
            raise ValidationError("Cannot add attachments to an archived task.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
