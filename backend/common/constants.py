from django.db import models

class ActionType(models.TextChoices):
    CREATED = 'CREATED', 'Created'
    UPDATED = 'UPDATED', 'Updated'
    DELETED = 'DELETED', 'Deleted'
    STATUS_CHANGED = 'STATUS_CHANGED', 'Status Changed'
    ASSIGNED = 'ASSIGNED', 'Assigned'
    LOGIN = 'LOGIN', 'Login'
    LOGOUT = 'LOGOUT', 'Logout'
    MEMBER_ADDED = 'MEMBER_ADDED', 'Member Added'
    MEMBER_REMOVED = 'MEMBER_REMOVED', 'Member Removed'
    MEMBER_ROLE_UPDATED = 'MEMBER_ROLE_UPDATED', 'Member Role Updated'
    LABEL_ASSIGNED = 'LABEL_ASSIGNED', 'Label Assigned'
    LABEL_REMOVED = 'LABEL_REMOVED', 'Label Removed'
    INVITATION_SENT = 'INVITATION_SENT', 'Invitation Sent'
    INVITATION_ACCEPTED = 'INVITATION_ACCEPTED', 'Invitation Accepted'
    INVITATION_DECLINED = 'INVITATION_DECLINED', 'Invitation Declined'
    INVITATION_REVOKED = 'INVITATION_REVOKED', 'Invitation Revoked'
    INVITATION_EXPIRED = 'INVITATION_EXPIRED', 'Invitation Expired'

class TargetType(models.TextChoices):
    PROJECT = 'PROJECT', 'Project'
    TASK = 'TASK', 'Task'
    USER = 'USER', 'User'
    PROJECT_MEMBER = 'PROJECT_MEMBER', 'Project Member'
    PROJECT_INVITATION = 'PROJECT_INVITATION', 'Project Invitation'
