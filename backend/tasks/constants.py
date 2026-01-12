from django.db import models

class TaskStatus(models.TextChoices):
    TODO = 'TODO', 'To Do'
    IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
    IN_REVIEW = 'IN_REVIEW', 'In Review'
    COMPLETED = 'COMPLETED', 'Completed'
    BLOCKED = 'BLOCKED', 'Blocked'

class TaskPriority(models.TextChoices):
    LOW = 'LOW', 'Low'
    MEDIUM = 'MEDIUM', 'Medium'
    HIGH = 'HIGH', 'High'
    URGENT = 'URGENT', 'Urgent'
