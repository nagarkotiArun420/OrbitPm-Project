from django.db import models

class NotificationType(models.TextChoices):
    TASK_ASSIGNED = 'TASK_ASSIGNED', 'Task Assigned'
    TASK_COMPLETED = 'TASK_COMPLETED', 'Task Completed'
    TASK_COMMENTED = 'TASK_COMMENTED', 'Task Commented'
    TASK_ARCHIVED = 'TASK_ARCHIVED', 'Task Archived'
    TASK_OVERDUE = 'TASK_OVERDUE', 'Task Overdue'
    TASK_DEADLINE_APPROACHING = 'TASK_DEADLINE_APPROACHING', 'Task Deadline Approaching'
    PROJECT_UPDATED = 'PROJECT_UPDATED', 'Project Updated'
    PROJECT_INVITATION_SENT = 'PROJECT_INVITATION_SENT', 'Project Invitation Sent'
    PROJECT_INVITATION_ACCEPTED = 'PROJECT_INVITATION_ACCEPTED', 'Project Invitation Accepted'
    PROJECT_INVITATION_DECLINED = 'PROJECT_INVITATION_DECLINED', 'Project Invitation Declined'
    PROJECT_INVITATION_REVOKED = 'PROJECT_INVITATION_REVOKED', 'Project Invitation Revoked'
    MEMBER_ADDED = 'MEMBER_ADDED', 'Member Added'
    MEMBER_ROLE_UPDATED = 'MEMBER_ROLE_UPDATED', 'Member Role Updated'
    MEMBER_REMOVED = 'MEMBER_REMOVED', 'Member Removed'

