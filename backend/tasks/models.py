import uuid
from django.db import models
from django.conf import settings
from projects.models import Project

class Task(models.Model):
    """
    Task model representing granular units of work within a Project.
    """
    class TaskStatus(models.TextChoices):
        TODO = 'TODO', 'To Do'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        REVIEW = 'REVIEW', 'Review'
        DONE = 'DONE', 'Done'

    class TaskPriority(models.TextChoices):
        LOW = 'LOW', 'Low'
        MEDIUM = 'MEDIUM', 'Medium'
        HIGH = 'HIGH', 'High'
        CRITICAL = 'CRITICAL', 'Critical'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    project = models.ForeignKey(
        Project, 
        on_delete=models.CASCADE, 
        related_name='tasks'
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='assigned_tasks'
    )
    status = models.CharField(
        max_length=20, 
        choices=TaskStatus.choices, 
        default=TaskStatus.TODO
    )
    priority = models.CharField(
        max_length=20, 
        choices=TaskPriority.choices, 
        default=TaskPriority.MEDIUM
    )
    due_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.status})"
