from django.db import transaction
from django.core.exceptions import ValidationError
from tasks.models import Task
from tasks.constants import TaskStatus

# Define standard agile status transition matrix
ALLOWED_TRANSITIONS = {
    TaskStatus.TODO: [TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED],
    TaskStatus.IN_PROGRESS: [TaskStatus.IN_REVIEW, TaskStatus.BLOCKED, TaskStatus.TODO],
    TaskStatus.IN_REVIEW: [TaskStatus.COMPLETED, TaskStatus.IN_PROGRESS, TaskStatus.TODO],
    TaskStatus.COMPLETED: [TaskStatus.TODO, TaskStatus.IN_PROGRESS],
    TaskStatus.BLOCKED: [TaskStatus.TODO, TaskStatus.IN_PROGRESS],
}

@transaction.atomic
def create_task(project, title, created_by=None, **kwargs):
    """
    Service layer method to safely instantiate and validate a Task.
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
def assign_task_to_user(task, user, assigned_by=None):
    """
    Business service to assign task to a user.
    Model-level clean() verifies if user is part of the project team.
    """
    task.assigned_to = user
    if assigned_by:
        task.assigned_by = assigned_by
    task.save()
    return task


@transaction.atomic
def transition_task_status(task, new_status):
    """
    State machine workflow transaction. Enforces valid Scrum status transitions
    and handles automatic lifecycle completion timestamps.
    """
    old_status = task.status
    if old_status == new_status:
        return task

    # Enforce workflow boundaries
    allowed = ALLOWED_TRANSITIONS.get(old_status, [])
    if new_status not in allowed:
        raise ValidationError(
            f"Invalid workflow status transition from '{old_status}' to '{new_status}'."
        )

    task.status = new_status
    # Triggers clean() which automatically configures completed_at timestamp
    task.save()
    return task
