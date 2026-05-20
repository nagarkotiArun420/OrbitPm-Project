from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
from notifications.models import Notification
from notifications.constants import NotificationType

User = get_user_model()


@transaction.atomic
def create_notification(recipient, actor, notification_type, title, message, metadata=None):
    """
    Decoupled business logic to issue a notification.
    Prevents self-notification if actor == recipient.
    """
    if recipient == actor:
        return None

    if metadata is None:
        metadata = {}

    notification = Notification.objects.create(
        recipient=recipient,
        actor=actor,
        notification_type=notification_type,
        title=title,
        message=message,
        metadata=metadata
    )
    return notification


@transaction.atomic
def mark_notification_as_read(notification, request=None):
    """
    Marks a notification record as read.
    """
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()
    return notification


@transaction.atomic
def mark_all_notifications_as_read(user, request=None):
    """
    Marks all unread notifications for the authenticated user as read.
    """
    unread = Notification.objects.filter(recipient=user, is_read=False)
    count = unread.count()
    unread.update(is_read=True, read_at=timezone.now())
    return count


@transaction.atomic
def notify_task_assignment(task, actor, request=None):
    """
    Generates a notification when a task is assigned to a user.
    """
    recipient = task.assigned_to
    if not recipient:
        return None

    title = "Task Assigned"
    message = f"You have been assigned to task '{task.title}' in project '{task.project.title}'."
    metadata = {
        'task_id': str(task.id),
        'task_slug': task.slug,
        'project_id': str(task.project.id),
        'project_title': task.project.title
    }

    return create_notification(
        recipient=recipient,
        actor=actor,
        notification_type=NotificationType.TASK_ASSIGNED,
        title=title,
        message=message,
        metadata=metadata
    )


@transaction.atomic
def notify_task_comment(comment, request=None):
    """
    Generates notifications for stakeholders when a task comment is created.
    Stakeholders include: task assignee, task creator, project manager, and project creator.
    """
    task = comment.task
    author = comment.author

    # Collect distinct potential recipients
    recipients = set()
    if task.assigned_to:
        recipients.add(task.assigned_to)
    if task.assigned_by:
        recipients.add(task.assigned_by)
    if task.project.manager:
        recipients.add(task.project.manager)
    if task.project.created_by:
        recipients.add(task.project.created_by)

    # Exclude comment author
    recipients.discard(author)

    title = f"New Comment on {task.title}"
    snippet = comment.content[:60] + "..." if len(comment.content) > 60 else comment.content
    message = f"{author.full_name or author.email} commented: \"{snippet}\""
    metadata = {
        'comment_id': str(comment.id),
        'task_id': str(task.id),
        'task_slug': task.slug,
        'project_id': str(task.project.id),
        'project_title': task.project.title
    }

    notifications = []
    for recipient in recipients:
        notif = create_notification(
            recipient=recipient,
            actor=author,
            notification_type=NotificationType.TASK_COMMENTED,
            title=title,
            message=message,
            metadata=metadata
        )
        if notif:
            notifications.append(notif)

    return notifications


@transaction.atomic
def notify_task_completion(task, actor, request=None):
    """
    Generates notifications for stakeholders when a task is completed.
    Stakeholders include: task creator, project manager, project creator, and task assignee (if not actor).
    """
    # Collect distinct potential recipients
    recipients = set()
    if task.assigned_by:
        recipients.add(task.assigned_by)
    if task.project.manager:
        recipients.add(task.project.manager)
    if task.project.created_by:
        recipients.add(task.project.created_by)
    if task.assigned_to:
        recipients.add(task.assigned_to)

    # Exclude completing actor
    if actor:
        recipients.discard(actor)

    actor_name = actor.full_name or actor.email if actor else "System"
    title = "Task Completed"
    message = f"Task '{task.title}' in project '{task.project.title}' has been marked completed by {actor_name}."
    metadata = {
        'task_id': str(task.id),
        'task_slug': task.slug,
        'project_id': str(task.project.id),
        'project_title': task.project.title
    }

    notifications = []
    for recipient in recipients:
        notif = create_notification(
            recipient=recipient,
            actor=actor,
            notification_type=NotificationType.TASK_COMPLETED,
            title=title,
            message=message,
            metadata=metadata
        )
        if notif:
            notifications.append(notif)

    return notifications


@transaction.atomic
def notify_project_update(project, actor, changes, request=None):
    """
    Generates notifications for project stakeholders when project metadata changes.
    Stakeholders include: all project team members, project manager, and project creator.
    """
    # Collect distinct potential recipients
    recipients = set()
    if project.manager:
        recipients.add(project.manager)
    if project.created_by:
        recipients.add(project.created_by)
    
    # Add project team members
    for member in project.team_members.all():
        recipients.add(member)

    # Exclude updating actor
    if actor:
        recipients.discard(actor)

    actor_name = actor.full_name or actor.email if actor else "System"
    title = "Project Updated"
    message = f"Project '{project.title}' was updated by {actor_name}."
    metadata = {
        'project_id': str(project.id),
        'project_title': project.title,
        'changes': changes
    }

    notifications = []
    for recipient in recipients:
        notif = create_notification(
            recipient=recipient,
            actor=actor,
            notification_type=NotificationType.PROJECT_UPDATED,
            title=title,
            message=message,
            metadata=metadata
        )
        if notif:
            notifications.append(notif)

    return notifications
