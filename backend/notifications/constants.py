from django.db import models

class NotificationType(models.TextChoices):
    TASK_ASSIGNED = 'TASK_ASSIGNED', 'Task Assigned'
    TASK_COMPLETED = 'TASK_COMPLETED', 'Task Completed'
    TASK_COMMENTED = 'TASK_COMMENTED', 'Task Commented'
    TASK_ARCHIVED = 'TASK_ARCHIVED', 'Task Archived'
    TASK_OVERDUE = 'TASK_OVERDUE', 'Task Overdue'
    TASK_DEADLINE_APPROACHING = 'TASK_DEADLINE_APPROACHING', 'Task Deadline Approaching'
    PROJECT_UPDATED = 'PROJECT_UPDATED', 'Project Updated'
