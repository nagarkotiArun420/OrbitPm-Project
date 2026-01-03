from django.core.exceptions import ValidationError
from tasks.constants import TaskStatus


# ──────────────────────────────────────────────────────────────
# Status Transition Matrix
# Defines valid agile workflow state transitions.
# ──────────────────────────────────────────────────────────────
ALLOWED_TRANSITIONS = {
    TaskStatus.TODO: [TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED],
    TaskStatus.IN_PROGRESS: [TaskStatus.IN_REVIEW, TaskStatus.BLOCKED],
    TaskStatus.IN_REVIEW: [TaskStatus.COMPLETED, TaskStatus.IN_PROGRESS],
    TaskStatus.BLOCKED: [TaskStatus.TODO, TaskStatus.IN_PROGRESS],
    TaskStatus.COMPLETED: [],
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


def get_valid_next_statuses(current_status):
    """
    Returns a list of allowed next status values from the current status.
    """
    return ALLOWED_TRANSITIONS.get(current_status, [])


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


def validate_task_assignment(task, new_assignee, actor):
    """
    Validates task assignment rules:
    - assigned users must belong to the related project team
    - clients cannot be assigned tasks
    - inactive users cannot receive assignments
    - completed tasks cannot be reassigned
    - only authorized roles can assign tasks
    """
    from accounts.models import User
    
    current_assignee = task.assigned_to if task.pk else None
    
    # Completed tasks cannot be reassigned
    if task.pk and task.status == TaskStatus.COMPLETED and current_assignee != new_assignee:
        raise ValidationError("Completed tasks cannot be reassigned.")
        
    if new_assignee:
        # Inactive users cannot receive assignments
        if not new_assignee.is_active:
            raise ValidationError("Inactive users cannot receive assignments.")
            
        # Clients cannot be assigned tasks
        if new_assignee.role == User.Roles.CLIENT:
            raise ValidationError("Clients cannot be assigned tasks.")
            
        # Assigned users must belong to the related project team
        validate_assignee_project_membership(new_assignee, task.project)
        
    # Role-Based Assignment Rules (authorized roles can assign tasks)
    if current_assignee != new_assignee:
        if not actor:
            raise ValidationError("An actor is required to perform task assignment validation.")
            
        if actor.role == User.Roles.ADMIN:
            pass  # Admin can assign any task
            
        elif actor.role == User.Roles.MANAGER:
            # Manager can assign tasks within managed projects
            is_managed = (
                task.project.manager == actor or
                task.project.created_by == actor
            )
            if not is_managed:
                raise ValidationError("Managers can only assign tasks within their managed projects.")
                
        elif actor.role == User.Roles.DEVELOPER:
            # Developer cannot assign tasks to others (can only self-assign or unassign)
            if new_assignee is not None and new_assignee != actor:
                raise ValidationError("Developers cannot assign tasks to other users.")
                
        elif actor.role == User.Roles.CLIENT:
            # Clients cannot assign tasks at all
            raise ValidationError("Clients cannot assign tasks.")
            
        else:
            raise ValidationError("Unauthorized role to perform task assignment.")
