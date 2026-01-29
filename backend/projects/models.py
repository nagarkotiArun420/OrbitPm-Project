import uuid
import secrets
from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.utils import timezone
from django.core.exceptions import ValidationError
from projects.constants import (
    ProjectInvitationStatus,
    ProjectStatus,
    ProjectPriority,
    ProjectMemberRole,
)
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


class ProjectMember(models.Model):
    """
    ProjectMember represents a user's membership within a specific project.
    Enables granular role-based team management at the project level.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='memberships'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='project_memberships'
    )
    role = models.CharField(
        max_length=20,
        choices=ProjectMemberRole.choices,
        default=ProjectMemberRole.DEVELOPER,
        db_index=True
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invited_memberships'
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('project', 'user')
        ordering = ['-joined_at']
        indexes = [
            models.Index(fields=['project', 'role']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.role} on {self.project.title}"

    def clean(self):
        super().clean()
        if self.user_id and hasattr(self, 'user') and not self.user.is_active:
            raise ValidationError({
                'user': 'Inactive users cannot be added as project members.'
            })


class ProjectInvitation(models.Model):
    """
    ProjectInvitation tracks a controlled invitation workflow before a user
    becomes an active project member.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='invitations',
    )
    invited_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='project_invitations',
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_project_invitations',
    )
    role = models.CharField(
        max_length=20,
        choices=ProjectMemberRole.choices,
        default=ProjectMemberRole.DEVELOPER,
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=ProjectInvitationStatus.choices,
        default=ProjectInvitationStatus.PENDING,
        db_index=True,
    )
    token = models.CharField(max_length=128, unique=True, db_index=True, blank=True)
    expires_at = models.DateTimeField(db_index=True)
    accepted_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(
                fields=['project', 'status'],
                name='projects_pr_project_1d057c_idx',
            ),
            models.Index(
                fields=['invited_user', 'status'],
                name='projects_pr_invited_85394f_idx',
            ),
            models.Index(
                fields=['expires_at', 'status'],
                name='projects_pr_expires_3c6ddd_idx',
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['project', 'invited_user'],
                condition=models.Q(status=ProjectInvitationStatus.PENDING),
                name='unique_pending_project_invitation',
            ),
        ]

    def __str__(self):
        return f"{self.invited_user.email} invited to {self.project.title} ({self.status})"

    @property
    def is_expired(self):
        return (
            self.status == ProjectInvitationStatus.PENDING and
            self.expires_at <= timezone.now()
        )

    def clean(self):
        super().clean()
        if self.invited_user_id and hasattr(self, 'invited_user') and not self.invited_user.is_active:
            raise ValidationError({
                'invited_user': 'Inactive users cannot receive project invitations.'
            })
        if self.accepted_at and self.status != ProjectInvitationStatus.ACCEPTED:
            raise ValidationError({
                'accepted_at': 'accepted_at can only be set for accepted invitations.'
            })

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = self.generate_unique_token()
        self.full_clean()
        super().save(*args, **kwargs)

    @classmethod
    def generate_unique_token(cls):
        while True:
            token = secrets.token_urlsafe(32)
            if not cls.objects.filter(token=token).exists():
                return token

