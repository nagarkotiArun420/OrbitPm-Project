from notifications.models import Notification

def send_in_app_notification(recipient, title, message):
    """
    Decoupled business logic to issue a notification.
    Can trigger background WebSockets/Email dispatches in production.
    """
    notification = Notification.objects.create(
        recipient=recipient,
        title=title,
        message=message
    )
    return notification

def mark_notification_as_read(notification_id):
    """
    Marks a notification record as read.
    """
    notification = Notification.objects.get(id=notification_id)
    notification.is_read = True
    notification.save()
    return notification
