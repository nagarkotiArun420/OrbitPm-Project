from django.db import transaction
from django.core.exceptions import ValidationError
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


# =========================================================
# TASK CRUD SERVICES
# =========================================================

@transaction.atomic
def create_task(project, title, created_by=None, request=None, **kwargs):
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
    task.save()

    log_task_activity(
        actor=created_by,
        task=task,
        action_type=ActionType.CREATED,
        description=f"Task '{task.title}' was created in project '{project.title}'.",
        request=request
    )

    # ✅ notification
    if task.assigned_to:
        from notifications.services import notify_task_assignment
        notify_task_assignment(task, actor=actor, request=request)

    return task


# =========================================================
# UPDATE TASK
# =========================================================

@transaction.atomic
def update_task(task, request=None, **validated_data):
    old_status = task.status
    old_assignee = task.assigned_to

    actor = request.user if request else None

    if 'assigned_to' in validated_data:
        validate_task_assignment(task, validated_data['assigned_to'], actor=actor)

    changes = get_model_changes(
        task,
        {k: v for k, v in validated_data.items() if k not in ['status', 'assigned_to']}
    )

    new_status = validated_data.get('status')
    if new_status and new_status != task.status:
        validate_status_transition(task.status, new_status)

    for field, value in validated_data.items():
        setattr(task, field, value)

    task.save()

    # ---------------- STATUS CHANGE ----------------
    if old_status != task.status:
        log_task_activity(
            actor=actor,
            task=task,
            action_type=ActionType.STATUS_CHANGED,
            description=f"Task '{task.title}' status changed from {old_status} to {task.status}.",
            metadata={'old_status': old_status, 'new_status': task.status},
            request=request
        )

        if task.status == TaskStatus.COMPLETED:
            from notifications.services import notify_task_completion
            notify_task_completion(task, actor=actor, request=request)

    # ---------------- ASSIGNEE CHANGE ----------------
    if old_assignee != task.assigned_to:
        old_email = old_assignee.email if old_assignee else None
        new_email = task.assigned_to.email if task.assigned_to else None

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

        if task.assigned_to:
            from notifications.services import notify_task_assignment
            notify_task_assignment(task, actor=actor, request=request)

    # ---------------- OTHER CHANGES ----------------
    if changes:
        log_task_activity(
            actor=actor,
            task=task,
            action_type=ActionType.UPDATED,
            description=f"Task '{task.title}' was updated.",
            metadata={'changes': changes},
            request=request
        )

    return task


# =========================================================
# ASSIGN TASK (DEDICATED SERVICE)
# =========================================================

@transaction.atomic
def assign_task_to_user(task, user, assigned_by=None, request=None):
    old_assignee = task.assigned_to

    if old_assignee == user:
        return task

    actor = request.user if request else assigned_by
    validate_task_assignment(task, user, actor=actor)

    task.assigned_to = user
    if assigned_by:
        task.assigned_by = assigned_by

    task.save()

    log_task_activity(
        actor=actor,
        task=task,
        action_type=ActionType.ASSIGNED,
        description=f"Task '{task.title}' was assigned to {user.email if user else 'Unassigned'}.",
        metadata={
            'old_assignee_email': old_assignee.email if old_assignee else None,
            'new_assignee_email': user.email if user else None
        },
        request=request
    )

    if user:
        from notifications.services import notify_task_assignment
        notify_task_assignment(task, actor=actor, request=request)

    return task


# =========================================================
# STATUS TRANSITION
# =========================================================

@transaction.atomic
def transition_task_status(task, new_status, request=None):
    old_status = task.status

    if old_status == new_status:
        return task

    validate_status_transition(old_status, new_status)

    task.status = new_status
    task.save()

    actor = request.user if request else None

    log_task_activity(
        actor=actor,
        task=task,
        action_type=ActionType.STATUS_CHANGED,
        description=f"Task '{task.title}' status changed from {old_status} to {new_status}.",
        metadata={'old_status': old_status, 'new_status': new_status},
        request=request
    )

    if new_status == TaskStatus.COMPLETED:
        from notifications.services import notify_task_completion
        notify_task_completion(task, actor=actor, request=request)

    return task


@transaction.atomic
def complete_task(task, request=None):
    return transition_task_status(task, TaskStatus.COMPLETED, request=request)