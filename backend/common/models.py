import uuid
from django.db import models
from django.conf import settings
from common.constants import ActionType, TargetType

class ActivityLog(models.Model):
    """
    ActivityLog model representing audit logs for project, task, and auth operations.
    Housed in the common app to avoid circular dependencies with other apps.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activity_logs'
    )
    
    action_type = models.CharField(
        max_length=50,
        choices=ActionType.choices,
        db_index=True
    )
    
    target_type = models.CharField(
        max_length=50,
        choices=TargetType.choices,
        db_index=True
    )
    
    target_id = models.CharField(
        max_length=255,
        db_index=True,
        null=True,
        blank=True
    )
    
    target_repr = models.CharField(
        max_length=255
    )
    
    description = models.TextField(
        blank=True,
        null=True
    )
    
    metadata = models.JSONField(
        default=dict,
        blank=True
    )
    
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['target_type', 'target_id']),
            models.Index(fields=['action_type']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        actor_email = self.actor.email if self.actor else "System"
        return f"{actor_email} - {self.action_type} - {self.target_type} ({self.target_repr}) at {self.created_at}"
