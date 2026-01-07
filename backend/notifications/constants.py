from django.db import models

class NotificationType(models.TextChoices):
    TASK_ASSIGNED = 'TASK_ASSIGNED', 'Task Assigned'
    TASK_COMPLETED = 'TASK_COMPLETED', 'Task Completed'
    TASK_COMMENTED = 'TASK_COMMENTED', 'Task Commented'
    TASK_ARCHIVED = 'TASK_ARCHIVED', 'Task Archived'
    PROJECT_UPDATED = 'PROJECT_UPDATED', 'Project Updated'
