from django.db import transaction
from django.core.exceptions import ValidationError
from tasks.models import Task
from tasks.constants import TaskStatus
from tasks.validators import (
    ALLOWED_TRANSITIONS,
    validate_status_transition,
    validate_assignee_project_membership,
    validate_due_date_within_project,
)


@transaction.atomic
def create_task(project, title, created_by=None, **kwargs):
    """
    Service layer method to safely instantiate and validate a Task.
    Triggers model clean() validations (team membership, due dates, etc.).
    """
    task = Task(
        project=project,
        title=title,
        assigned_by=created_by,
        **kwargs
    )
    # Triggers model clean() validations (assigned_to team member check, due dates, etc.)
    task.save()
    return task


@transaction.atomic
def update_task(task, **validated_data):
    """
    Service layer method to safely update a Task.
    Handles status transition validation if status is being changed,
    then synchronizes all attributes under a transaction.
    """
    new_status = validated_data.get('status')
    if new_status and new_status != task.status:
        validate_status_transition(task.status, new_status)

    # Update baseline attributes
    for field, value in validated_data.items():
        setattr(task, field, value)

    # Triggers clean() which handles lifecycle logic (completed_at, etc.)
    task.save()
    return task


@transaction.atomic
def delete_task(task):
    """
    Service layer method to safely delete a Task.
    Ensures deletion occurs within a transaction boundary.
    """
    task.delete()


@transaction.atomic
def assign_task_to_user(task, user, assigned_by=None):
    """
    Business service to assign a task to a user.
    Model-level clean() verifies if the user is part of the project team.
    """
    task.assigned_to = user
    if assigned_by:
        task.assigned_by = assigned_by
    task.save()
    return task


@transaction.atomic
def transition_task_status(task, new_status):
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
    return task


@transaction.atomic
def complete_task(task):
    """
    Convenience service to transition a task to COMPLETED status.
    Validates the transition is legal and delegates to the standard
    transition service which auto-sets completed_at via model clean().
    """
    return transition_task_status(task, TaskStatus.COMPLETED)
