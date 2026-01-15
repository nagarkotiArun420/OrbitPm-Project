from datetime import timedelta
from django.db import transaction
from django.core.exceptions import ValidationError
from django.conf import settings
from django.utils import timezone
from tasks.models import Task, TaskComment
from tasks.constants import TaskStatus
from tasks.validators import (
    ALLOWED_TRANSITIONS,
    validate_status_transition,
    validate_assignee_project_membership,
    validate_due_date_within_project,
    validate_task_assignment,
)
from common.services import log_task_activity
from common.constants import ActionType
from common.utils import get_model_changes
from notifications.constants import NotificationType
from notifications.models import Notification
from notifications.services import send_in_app_notification


@transaction.atomic
def create_task(project, title, created_by=None, request=None, **kwargs):
    """
    Service layer method to safely instantiate and validate a Task.
    Triggers model clean() validations (team membership, due dates, etc.).
    """
    assigned_to = kwargs.get('assigned_to')
    temp_task = Task(project=project, assigned_to=assigned_to)
    actor = request.user if request else created_by
    validate_task_assignment(temp_task, assigned_to, actor=actor)

    task = Task(
        project=project,
        title=title,
        assigned_by=created_by,
        **kwargs
    )
    # Triggers model clean() validations (assigned_to team member check, due dates, etc.)
    task.save()
    
    log_task_activity(
        actor=created_by,
        task=task,
        action_type=ActionType.CREATED,
        description=f"Task '{task.title}' was created in project '{project.title}'.",
        request=request
    )
    
    return task


@transaction.atomic
def update_task(task, request=None, **validated_data):
    """
    Service layer method to safely update a Task.
    Handles status transition validation if status is being changed,
    then synchronizes all attributes under a transaction.
    """
    old_status = task.status
    old_assignee = task.assigned_to
    
    actor = request.user if request else None
    if 'assigned_to' in validated_data:
        validate_task_assignment(task, validated_data['assigned_to'], actor=actor)
    
    # Calculate changes for general fields (excluding status/assignee, which are logged separately)
    changes = get_model_changes(task, {k: v for k, v in validated_data.items() if k not in ['status', 'assigned_to']})
    
    new_status = validated_data.get('status')
    if new_status and new_status != task.status:
        validate_status_transition(task.status, new_status)

    # Update baseline attributes
    for field, value in validated_data.items():
        setattr(task, field, value)

    # Triggers clean() which handles lifecycle logic (completed_at, etc.)
    task.save()
    
    # Log status changed
    if old_status != task.status:
        log_task_activity(
            actor=request.user if request else None,
            task=task,
            action_type=ActionType.STATUS_CHANGED,
            description=f"Task '{task.title}' status changed from {old_status} to {task.status}.",
            metadata={
                'old_status': old_status,
                'new_status': task.status
            },
            request=request
        )
        
    # Log assignee changed
    if old_assignee != task.assigned_to:
        old_email = old_assignee.email if old_assignee else None
        new_email = task.assigned_to.email if task.assigned_to else None
        log_task_activity(
            actor=request.user if request else None,
            task=task,
            action_type=ActionType.ASSIGNED,
            description=f"Task '{task.title}' was assigned to {new_email or 'Unassigned'}.",
            metadata={
                'old_assignee_email': old_email,
                'new_assignee_email': new_email
            },
            request=request
        )
        
    # Log general updates
    if changes:
        log_task_activity(
            actor=request.user if request else None,
            task=task,
            action_type=ActionType.UPDATED,
            description=f"Task '{task.title}' was updated.",
            metadata={'changes': changes},
            request=request
        )
        
    return task


@transaction.atomic
def delete_task(task, request=None):
    """
    Service layer method to safely soft delete a Task.
    Sets is_deleted=True, recording deletion details, and logs the activity.
    """
    actor = request.user if request else None
    task.is_deleted = True
    task.deleted_at = timezone.now()
    task.deleted_by = actor
    task.save()
    
    log_task_activity(
        actor=actor,
        task=task,
        action_type=ActionType.DELETED,
        description=f"Task '{task.title}' was soft deleted.",
        request=request
    )


def check_recovery_permission(task, actor, action):
    """
    Checks if an actor has permission to perform restore/archive/unarchive.
    ADMIN: full access
    MANAGER: only in managed/created projects
    DEVELOPER: cannot restore. Can unarchive if assigned to them.
    CLIENT: no access
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    if not actor:
        raise ValidationError("Authentication is required.")
        
    if actor.role == User.Roles.ADMIN:
        return True
        
    if actor.role == User.Roles.MANAGER:
        # Check if project manager or project creator
        is_managed = (
            task.project.manager == actor or
            task.project.created_by == actor
        )
        if is_managed:
            return True
        raise ValidationError("Managers can only manage tasks in their own projects.")
        
    if actor.role == User.Roles.DEVELOPER:
        if action == 'unarchive':
            if task.assigned_to == actor:
                return True
            raise ValidationError("Developers can only unarchive tasks assigned to them.")
        raise ValidationError("Developers are not authorized to restore deleted tasks or archive tasks.")
        
    raise ValidationError("Clients are not authorized to manage task lifecycles.")


@transaction.atomic
def archive_task(task, request=None):
    """
    Business service to archive a completed task.
    """
    actor = request.user if request else None
    check_recovery_permission(task, actor, 'archive')
    
    if task.is_deleted:
        raise ValidationError("Cannot archive a deleted task.")
        
    if task.is_archived:
        raise ValidationError("Task is already archived.")
        
    if task.status != TaskStatus.COMPLETED:
        raise ValidationError("Only completed tasks can be archived.")
        
    task.is_archived = True
    task.archived_at = timezone.now()
    task.save()
    
    log_task_activity(
        actor=actor,
        task=task,
        action_type=ActionType.UPDATED,
        description=f"Task '{task.title}' was archived.",
        request=request
    )
    return task


@transaction.atomic
def restore_task(task, request=None):
    """
    Business service to restore a soft-deleted task.
    """
    actor = request.user if request else None
    check_recovery_permission(task, actor, 'restore')
    
    if not task.project:
        raise ValidationError("Cannot restore task because the project does not exist.")
        
    if not task.is_deleted:
        raise ValidationError("Task is not deleted.")
        
    task.is_deleted = False
    task.deleted_at = None
    task.deleted_by = None
    task.save()
    
    log_task_activity(
        actor=actor,
        task=task,
        action_type=ActionType.UPDATED,
        description=f"Task '{task.title}' was restored.",
        request=request
    )
    return task


@transaction.atomic
def unarchive_task(task, request=None):
    """
    Business service to unarchive an archived task.
    """
    actor = request.user if request else None
    check_recovery_permission(task, actor, 'unarchive')
    
    if task.is_deleted:
        raise ValidationError("Cannot unarchive a deleted task.")
        
    if not task.is_archived:
        raise ValidationError("Task is not archived.")
        
    task.is_archived = False
    task.archived_at = None
    task.save()
    
    log_task_activity(
        actor=actor,
        task=task,
        action_type=ActionType.UPDATED,
        description=f"Task '{task.title}' was unarchived.",
        request=request
    )
    return task


@transaction.atomic
def assign_task_to_user(task, user, assigned_by=None, request=None):
    """
    Business service to assign a task to a user.
    Model-level clean() verifies if the user is part of the project team.
    """
    old_assignee = task.assigned_to
    if old_assignee == user:
        return task
        
    actor = request.user if request else assigned_by
    validate_task_assignment(task, user, actor=actor)

    task.assigned_to = user
    if assigned_by:
        task.assigned_by = assigned_by
    task.save()
    
    actor = request.user if request else assigned_by
    old_email = old_assignee.email if old_assignee else None
    new_email = user.email if user else None
    
    log_task_activity(
        actor=actor,
        task=task,
        action_type=ActionType.ASSIGNED,
        description=f"Task '{task.title}' was assigned to {new_email or 'Unassigned'}.",
        metadata={
            'old_assignee_email': old_email,
            'new_assignee_email': new_email
        },
        request=request
    )
    return task


@transaction.atomic
def transition_task_status(task, new_status, request=None):
    """
    State machine workflow transition. Enforces valid Scrum status transitions
    and handles automatic lifecycle completion timestamps via model clean().
    """
    old_status = task.status
    if old_status == new_status:
        return task

    # Enforce workflow boundaries
    validate_status_transition(old_status, new_status)

    task.status = new_status
    # Triggers clean() which automatically configures completed_at timestamp
    task.save()
    
    log_task_activity(
        actor=request.user if request else None,
        task=task,
        action_type=ActionType.STATUS_CHANGED,
        description=f"Task '{task.title}' status changed from {old_status} to {new_status}.",
        metadata={
            'old_status': old_status,
            'new_status': new_status
        },
        request=request
    )
    return task


@transaction.atomic
def complete_task(task, request=None):
    """
    Convenience service to transition a task to COMPLETED status.
    Validates the transition is legal and delegates to the standard
    transition service which auto-sets completed_at via model clean().
    """
    return transition_task_status(task, TaskStatus.COMPLETED, request=request)


def check_comment_creation_permission(task, author):
    """
    Checks if a user is authorized to create comments on a task.
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    if not author or not author.is_authenticated:
        raise ValidationError("Authentication is required.")
        
    if author.role == User.Roles.ADMIN:
        return True
        
    if author.role == User.Roles.MANAGER:
        is_managed = (
            task.project.manager == author or
            task.project.created_by == author
        )
        if is_managed:
            return True
        raise ValidationError("Managers can only comment on tasks in their own projects.")
        
    if author.role == User.Roles.DEVELOPER:
        if task.assigned_to == author:
            return True
        raise ValidationError("Developers can only comment on tasks assigned to them.")
        
    raise ValidationError("Clients and other roles are not authorized to comment on tasks.")


def check_comment_edit_permission(comment, editor):
    """
    Checks if a user is authorized to edit a task comment.
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    if not editor or not editor.is_authenticated:
        raise ValidationError("Authentication is required.")
        
    if editor.role == User.Roles.ADMIN:
        return True
        
    if comment.author == editor:
        # Check task assignment rules if developer
        if editor.role == User.Roles.DEVELOPER:
            if comment.task.assigned_to != editor:
                raise ValidationError("Developers can only edit comments on tasks currently assigned to them.")
        return True
        
    raise ValidationError("You do not have permission to edit this comment.")


def check_comment_delete_permission(comment, actor):
    """
    Checks if a user is authorized to delete a task comment.
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    if not actor or not actor.is_authenticated:
        raise ValidationError("Authentication is required.")
        
    if actor.role == User.Roles.ADMIN:
        return True
        
    if actor.role == User.Roles.MANAGER:
        is_managed = (
            comment.task.project.manager == actor or
            comment.task.project.created_by == actor
        )
        if is_managed:
            return True
            
    if comment.author == actor:
        return True
        
    raise ValidationError("You do not have permission to delete this comment.")


@transaction.atomic
def create_comment(task, author, content, request=None):
    """
    Creates a new comment on a task with permission checks.
    """
    check_comment_creation_permission(task, author)
    
    comment = TaskComment(task=task, author=author, content=content)
    comment.full_clean()
    comment.save()
    
    log_task_activity(
        actor=author,
        task=task,
        action_type=ActionType.UPDATED,
        description=f"Comment added to task '{task.title}' by {author.email}.",
        request=request
    )
    return comment


@transaction.atomic
def update_comment(comment, editor, content, request=None):
    """
    Updates an existing task comment.
    """
    check_comment_edit_permission(comment, editor)
    
    if comment.task.is_deleted:
        raise ValidationError("Cannot modify comments on a deleted task.")
        
    if not content or not content.strip():
        raise ValidationError("Comment content cannot be empty.")
        
    comment.content = content
    comment.is_edited = True
    comment.edited_at = timezone.now()
    comment.full_clean()
    comment.save()
    
    log_task_activity(
        actor=editor,
        task=comment.task,
        action_type=ActionType.UPDATED,
        description=f"Comment on task '{comment.task.title}' was updated.",
        request=request
    )
    return comment


@transaction.atomic
def delete_comment(comment, actor, request=None):
    """
    Soft-deletes a task comment.
    """
    check_comment_delete_permission(comment, actor)
    
    comment.is_deleted = True
    comment.save()
    
    log_task_activity(
        actor=actor,
        task=comment.task,
        action_type=ActionType.DELETED,
        description=f"Comment on task '{comment.task.title}' was deleted.",
        request=request
    )
    return comment


def check_attachment_delete_permission(attachment, actor):
    """
    Checks if a user is authorized to delete a task attachment.
    ADMIN: full access.
    MANAGER: manage attachments within managed/created projects.
    DEVELOPER: delete attachments on tasks assigned to them.
    CLIENT: no delete access.
    """
    from accounts.models import User
    
    if not actor or not actor.is_authenticated:
        raise ValidationError("Authentication is required.")
        
    if actor.role == User.Roles.ADMIN:
        return True
        
    if actor.role == User.Roles.MANAGER:
        is_managed = (
            attachment.task.project.manager == actor or
            attachment.task.project.created_by == actor
        )
        if is_managed:
            return True
        raise ValidationError("Managers can only delete attachments within their managed projects.")
        
    if actor.role == User.Roles.DEVELOPER:
        if attachment.task.assigned_to == actor:
            return True
        raise ValidationError("Developers can only delete attachments on tasks assigned to them.")
        
    raise ValidationError("Clients are not authorized to delete attachments.")


@transaction.atomic
def create_attachment(task, uploaded_by, file, request=None):
    """
    Creates a new file attachment for a task, performing all validations
    and logging the activity.
    """
    from tasks.models import TaskAttachment
    from tasks.validators import validate_attachment_file
    import mimetypes
    
    # 1. Check if task is deleted
    if task.is_deleted:
        raise ValidationError("Cannot upload attachments to a deleted task.")
        
    # 2. Check if task is archived
    if task.is_archived:
        raise ValidationError("Cannot upload attachments to an archived task.")
        
    # 3. Validate uploaded file size & type
    validate_attachment_file(file)
    
    # 4. Extract metadata
    original_filename = file.name
    file_size = file.size
    mime_type = getattr(file, 'content_type', None)
    if not mime_type:
        mime_type, _ = mimetypes.guess_type(original_filename)
    if not mime_type:
        mime_type = 'application/octet-stream'
        
    # 5. Create instance
    attachment = TaskAttachment(
        task=task,
        uploaded_by=uploaded_by,
        file=file,
        original_filename=original_filename,
        file_size=file_size,
        mime_type=mime_type
    )
    attachment.full_clean()
    attachment.save()
    
    # 6. Log activity
    log_task_activity(
        actor=uploaded_by,
        task=task,
        action_type=ActionType.UPDATED,
        description=f"Attachment '{attachment.original_filename}' was uploaded to task '{task.title}'.",
        metadata={
            'attachment_id': str(attachment.id),
            'filename': attachment.original_filename,
            'file_size': attachment.file_size,
            'mime_type': attachment.mime_type
        },
        request=request
    )
    
    return attachment


@transaction.atomic
def delete_attachment(attachment, actor, request=None):
    """
    Deletes a task attachment physically and from database, and logs activity.
    """
    check_attachment_delete_permission(attachment, actor)
    
    task = attachment.task
    original_filename = attachment.original_filename
    attachment_id = attachment.id
    
    # Delete physically
    if attachment.file:
        attachment.file.delete(save=False)
        
    # Delete database record
    attachment.delete()
    
    # Log activity
    log_task_activity(
        actor=actor,
        task=task,
        action_type=ActionType.UPDATED,
        description=f"Attachment '{original_filename}' was deleted from task '{task.title}'.",
        metadata={
            'attachment_id': str(attachment_id),
            'filename': original_filename
        },
        request=request
    )


def get_deadline_warning_days():
    """
    Returns the configured approaching-deadline threshold.
    """
    return getattr(settings, 'TASK_DEADLINE_WARNING_DAYS', 3)


def get_upcoming_deadlines(days=None, queryset=None, reference_date=None):
    """
    Returns active, incomplete tasks with deadlines approaching within the warning window.
    """
    if days is None:
        days = get_deadline_warning_days()
    if queryset is None:
        queryset = Task.objects.all()
    reference_date = reference_date or timezone.localdate()
    end_date = reference_date + timedelta(days=days)
    return queryset.incomplete().filter(
        due_date__gte=reference_date,
        due_date__lte=end_date,
    ).select_related('project', 'assigned_to', 'project__manager')


def detect_overdue_tasks(queryset=None, reference_date=None):
    """
    Returns active, incomplete tasks whose due date has passed.
    """
    if queryset is None:
        queryset = Task.objects.all()
    return queryset.overdue(reference_date=reference_date).select_related(
        'project',
        'assigned_to',
        'project__manager',
    )


def _deadline_recipients(task):
    """
    Collects users who should receive deadline visibility notifications.
    """
    recipients = []
    seen = set()
    for user in (task.assigned_to, task.project.manager):
        if user and user.id not in seen:
            recipients.append(user)
            seen.add(user.id)
    return recipients


def _send_unique_deadline_notification(
    recipient,
    title,
    message,
    reference_date,
    notification_type,
    metadata=None
):
    exists = Notification.objects.filter(
        recipient=recipient,
        title=title,
        message=message,
        created_at__date=reference_date,
    ).exists()
    if exists:
        return None
    return send_in_app_notification(
        recipient=recipient,
        title=title,
        message=message,
        notification_type=notification_type,
        metadata=metadata,
    )


@transaction.atomic
def generate_overdue_task_notifications(queryset=None, reference_date=None):
    """
    Creates in-app notification and activity events for currently overdue tasks.
    Intended to be called by a future scheduled job or admin workflow.
    """
    reference_date = reference_date or timezone.localdate()
    tasks = list(detect_overdue_tasks(queryset=queryset, reference_date=reference_date))
    notifications = []

    for task in tasks:
        days_overdue = (reference_date - task.due_date).days
        title = 'Task overdue'
        message = (
            f"Task '{task.title}' was due on {task.due_date.isoformat()} "
            f"and is {days_overdue} day(s) overdue."
        )
        created_notifications = [
            notification
            for recipient in _deadline_recipients(task)
            for notification in [
                _send_unique_deadline_notification(
                    recipient=recipient,
                    title=title,
                    message=message,
                    reference_date=reference_date,
                    notification_type=NotificationType.TASK_OVERDUE,
                    metadata={
                        'task_id': str(task.id),
                        'deadline_event': 'overdue_detected',
                        'due_date': task.due_date.isoformat(),
                        'days_overdue': days_overdue,
                    },
                )
            ]
            if notification is not None
        ]
        notifications.extend(created_notifications)

        if created_notifications:
            log_task_activity(
                actor=None,
                task=task,
                action_type=ActionType.UPDATED,
                description=f"Task '{task.title}' was detected as overdue.",
                metadata={
                    'deadline_event': 'overdue_detected',
                    'due_date': task.due_date.isoformat(),
                    'days_overdue': days_overdue,
                }
            )

    return notifications


@transaction.atomic
def generate_upcoming_deadline_notifications(days=None, queryset=None, reference_date=None):
    """
    Creates in-app notification and activity events for tasks nearing their deadline.
    """
    reference_date = reference_date or timezone.localdate()
    tasks = list(get_upcoming_deadlines(
        days=days,
        queryset=queryset,
        reference_date=reference_date,
    ))
    notifications = []

    for task in tasks:
        days_until_due = (task.due_date - reference_date).days
        title = 'Task deadline approaching'
        message = (
            f"Task '{task.title}' is due on {task.due_date.isoformat()} "
            f"in {days_until_due} day(s)."
        )
        created_notifications = [
            notification
            for recipient in _deadline_recipients(task)
            for notification in [
                _send_unique_deadline_notification(
                    recipient=recipient,
                    title=title,
                    message=message,
                    reference_date=reference_date,
                    notification_type=NotificationType.TASK_DEADLINE_APPROACHING,
                    metadata={
                        'task_id': str(task.id),
                        'deadline_event': 'deadline_approaching',
                        'due_date': task.due_date.isoformat(),
                        'days_until_due': days_until_due,
                    },
                )
            ]
            if notification is not None
        ]
        notifications.extend(created_notifications)

        if created_notifications:
            log_task_activity(
                actor=None,
                task=task,
                action_type=ActionType.UPDATED,
                description=f"Task '{task.title}' deadline is approaching.",
                metadata={
                    'deadline_event': 'deadline_approaching',
                    'due_date': task.due_date.isoformat(),
                    'days_until_due': days_until_due,
                }
            )

    return notifications
