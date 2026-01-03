from django.db import transaction
from django.core.exceptions import ValidationError
from tasks.models import Task
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
    Service layer method to safely delete a Task.
    Ensures deletion occurs within a transaction boundary.
    """
    log_task_activity(
        actor=request.user if request else None,
        task=task,
        action_type=ActionType.DELETED,
        description=f"Task '{task.title}' was deleted.",
        request=request
    )
    task.delete()


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

