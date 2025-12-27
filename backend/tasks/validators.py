from django.core.exceptions import ValidationError
from tasks.constants import TaskStatus


# ──────────────────────────────────────────────────────────────
# Status Transition Matrix
# Defines valid agile workflow state transitions.
# ──────────────────────────────────────────────────────────────
ALLOWED_TRANSITIONS = {
    TaskStatus.TODO: [TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED],
    TaskStatus.IN_PROGRESS: [TaskStatus.IN_REVIEW, TaskStatus.BLOCKED, TaskStatus.TODO],
    TaskStatus.IN_REVIEW: [TaskStatus.COMPLETED, TaskStatus.IN_PROGRESS, TaskStatus.TODO],
    TaskStatus.COMPLETED: [TaskStatus.TODO, TaskStatus.IN_PROGRESS],
    TaskStatus.BLOCKED: [TaskStatus.TODO, TaskStatus.IN_PROGRESS],
}


def validate_hours_non_negative(value):
    """
    Ensures that hours estimated or actual are not a negative value.
    """
    if value is not None and value < 0:
        raise ValidationError("Hours cannot be negative.")


def validate_status_transition(current_status, new_status):
    """
    Validates that a status transition follows the allowed agile workflow matrix.
    Raises ValidationError with a descriptive message on invalid transitions.
    """
    if current_status == new_status:
        return  # No-op transitions are always valid

    allowed = ALLOWED_TRANSITIONS.get(current_status, [])
    if new_status not in allowed:
        allowed_labels = [dict(TaskStatus.choices).get(s, s) for s in allowed]
        raise ValidationError(
            f"Invalid status transition from '{current_status}' to '{new_status}'. "
            f"Allowed transitions: {', '.join(allowed_labels) or 'none'}."
        )


def validate_due_date_within_project(due_date, project):
    """
    Validates that a task's due date falls within the project's
    start_date → deadline bounds.
    """
    if not due_date or not project:
        return

    if project.start_date and due_date < project.start_date:
        raise ValidationError(
            "The task due date cannot be before the project start date "
            f"({project.start_date})."
        )
    if project.deadline and due_date > project.deadline:
        raise ValidationError(
            "The task due date cannot be after the project deadline "
            f"({project.deadline})."
        )


def validate_assignee_project_membership(user, project):
    """
    Validates that the assigned user is a legitimate member of the project:
    must be the project manager, creator, or an explicit team member.
    """
    if not user or not project:
        return

    is_team_member = (
        project.team_members.filter(id=user.id).exists() or
        project.manager == user or
        project.created_by == user
    )
    if not is_team_member:
        raise ValidationError(
            "The assigned user must be a member of the project team."
        )
