from django.db import models

class ActionType(models.TextChoices):
    CREATED = 'CREATED', 'Created'
    UPDATED = 'UPDATED', 'Updated'
    DELETED = 'DELETED', 'Deleted'
    STATUS_CHANGED = 'STATUS_CHANGED', 'Status Changed'
    ASSIGNED = 'ASSIGNED', 'Assigned'
    LOGIN = 'LOGIN', 'Login'
    LOGOUT = 'LOGOUT', 'Logout'

class TargetType(models.TextChoices):
    PROJECT = 'PROJECT', 'Project'
    TASK = 'TASK', 'Task'
    USER = 'USER', 'User'
