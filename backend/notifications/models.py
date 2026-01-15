import uuid
from django.db import models
from django.conf import settings
from notifications.constants import NotificationType


class NotificationQuerySet(models.QuerySet):
    """
    Custom QuerySet for the Notification model providing reusable filters.
    """
    def unread(self):
        """Filter only unread notifications."""
        return self.filter(is_read=False)

    def read(self):
        """Filter only read notifications."""
        return self.filter(is_read=True)

    def recent(self):
        """Sort notifications in descending chronological order."""
        return self.order_by('-created_at')


class Notification(models.Model):
    """
    Notification model representing in-app message logs and workflow events for users.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relationships
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        db_index=True
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='actor_notifications',
        null=True,
        blank=True
    )
    
    # Fields
    notification_type = models.CharField(
        max_length=50,
        choices=NotificationType.choices,
        db_index=True
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    # Attach the custom manager
    objects = NotificationQuerySet.as_manager()

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read'], name='notificatio_recipie_4e3567_idx'),
        ]

    def __str__(self):
        return f"{self.title} - {self.recipient.email} (Type: {self.notification_type}, Read: {self.is_read})"
