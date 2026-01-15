from django.utils import timezone
from notifications.constants import NotificationType
from notifications.models import Notification

def send_in_app_notification(
    recipient,
    title,
    message,
    notification_type=NotificationType.PROJECT_UPDATED,
    actor=None,
    metadata=None
):
    """
    Decoupled business logic to issue a notification.
    Can trigger background WebSockets/Email dispatches in production.
    """
    notification = Notification.objects.create(
        recipient=recipient,
        actor=actor,
        notification_type=notification_type,
        title=title,
        message=message,
        metadata=metadata or {},
    )
    return notification

def mark_notification_as_read(notification_id):
    """
    Marks a notification record as read.
    """
    notification = Notification.objects.get(id=notification_id)
    notification.is_read = True
    notification.read_at = timezone.now()
    notification.save()
    return notification
