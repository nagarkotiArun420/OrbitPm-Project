import uuid
from django.db import models
from django.conf import settings

class Project(models.Model):
    """
    Project model representing an agency engagement or workflow.
    """
    class ProjectStatus(models.TextChoices):
        PLANNING = 'PLANNING', 'Planning'
        ACTIVE = 'ACTIVE', 'Active'
        COMPLETED = 'COMPLETED', 'Completed'
        ON_HOLD = 'ON_HOLD', 'On Hold'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=20, 
        choices=ProjectStatus.choices, 
        default=ProjectStatus.PLANNING
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='owned_projects'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
