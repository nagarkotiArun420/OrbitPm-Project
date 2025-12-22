import uuid
from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.utils import timezone
from django.core.exceptions import ValidationError
from projects.constants import ProjectStatus, ProjectPriority
from projects.validators import validate_budget_positive

class Project(models.Model):
    """
    Project model representing an agency engagement or workflow workspace in OrbitPM.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    
    status = models.CharField(
        max_length=20,
        choices=ProjectStatus.choices,
        default=ProjectStatus.PLANNING,
        db_index=True
    )
    priority = models.CharField(
        max_length=20,
        choices=ProjectPriority.choices,
        default=ProjectPriority.MEDIUM,
        db_index=True
    )
    
    start_date = models.DateField(blank=True, null=True)
    deadline = models.DateField(blank=True, null=True, db_index=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    budget = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        blank=True, 
        null=True,
        validators=[validate_budget_positive]
    )
    
    # Relationships
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='client_projects'
    )
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_projects'
    )
    team_members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='team_projects'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_projects'
    )
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.status})"

    def clean(self):
        super().clean()
        
        # Validation for deadline alignment
        if self.start_date and self.deadline:
            if self.deadline < self.start_date:
                raise ValidationError({
                    'deadline': 'The project deadline cannot be before the start date.'
                })
        
        # Lifecycle logic: automatic completed_at adjustments
        if self.status == ProjectStatus.COMPLETED:
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
            # Perform query excluding current record (in case of updates)
            while Project.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
            
        self.full_clean()
        super().save(*args, **kwargs)
