import uuid
from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.utils import timezone
from django.core.exceptions import ValidationError
from projects.models import Project
from tasks.constants import TaskStatus, TaskPriority
from tasks.validators import validate_hours_non_negative

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
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.status})"

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
