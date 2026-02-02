from django.utils import timezone
from notifications.constants import NotificationType
from notifications.models import Notification, NotificationPreference


_NOTIFICATION_PREFERENCE_FIELD_MAP = {
    NotificationType.TASK_ASSIGNED: 'task_assignment_enabled',
    NotificationType.TASK_COMMENTED: 'task_comment_enabled',
    NotificationType.TASK_DEADLINE_APPROACHING: 'task_deadline_enabled',
    NotificationType.TASK_OVERDUE: 'task_deadline_enabled',
    NotificationType.PROJECT_UPDATED: 'project_update_enabled',
    NotificationType.MEMBER_ADDED: 'project_update_enabled',
    NotificationType.MEMBER_REMOVED: 'project_update_enabled',
    NotificationType.MEMBER_ROLE_UPDATED: 'project_update_enabled',
    NotificationType.PROJECT_INVITATION_SENT: 'invitation_enabled',
    NotificationType.PROJECT_INVITATION_ACCEPTED: 'invitation_enabled',
    NotificationType.PROJECT_INVITATION_DECLINED: 'invitation_enabled',
    NotificationType.PROJECT_INVITATION_REVOKED: 'invitation_enabled',
}


def get_user_preferences(user):
    """
    Returns (and creates if needed) the user's notification preferences.
    """
    if user is None:
        return None
    prefs, _ = NotificationPreference.objects.select_related('user').get_or_create(user=user)
    return prefs


def should_send_notification(recipient, notification_type):
    """
    Returns True when the recipient has the corresponding preference enabled.
    Unknown notification types default to enabled.
    """
    if recipient is None:
        return False
    if hasattr(recipient, 'is_active') and not recipient.is_active:
        return False

    preference_field = _NOTIFICATION_PREFERENCE_FIELD_MAP.get(notification_type)
    if preference_field is None:
        return True

    prefs = get_user_preferences(recipient)
    return bool(getattr(prefs, preference_field, True))

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
    if not should_send_notification(recipient, notification_type):
        return None

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
