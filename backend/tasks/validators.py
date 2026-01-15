from django.core.exceptions import ValidationError
from tasks.constants import TaskStatus
import os
import mimetypes

ALLOWED_TRANSITIONS = {
    TaskStatus.TODO: [TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED],
    TaskStatus.IN_PROGRESS: [TaskStatus.IN_REVIEW, TaskStatus.BLOCKED],
    TaskStatus.IN_REVIEW: [TaskStatus.COMPLETED, TaskStatus.IN_PROGRESS],
    TaskStatus.BLOCKED: [TaskStatus.TODO, TaskStatus.IN_PROGRESS],
    TaskStatus.COMPLETED: [],
}


def validate_hours_non_negative(value):
    if value is not None and value < 0:
        raise ValidationError("Hours cannot be negative.")


def get_valid_next_statuses(current_status):
    return ALLOWED_TRANSITIONS.get(current_status, [])


def validate_status_transition(current_status, new_status):
    if current_status == new_status:
        return
    if new_status not in get_valid_next_statuses(current_status):
        raise ValidationError(
            f"Invalid status transition from {current_status} to {new_status}."
        )


def validate_due_date_within_project(due_date, project):
    if not due_date or not project:
        return
    if project.start_date and due_date < project.start_date:
        raise ValidationError("The task due date cannot be before the project start date.")
    if project.deadline and due_date > project.deadline:
        raise ValidationError("The task due date cannot be after the project deadline.")


def validate_assignee_project_membership(task, assignee):
    if not assignee or not task or not task.project:
        return

    is_team_member = (
        task.project.team_members.filter(id=assignee.id).exists() or
        task.project.manager_id == assignee.id or
        task.project.created_by_id == assignee.id
    )
    if not is_team_member:
        raise ValidationError("The assigned user must belong to the project team.")


def validate_task_assignment(task, assignee, actor=None):
    """
    Validates assignment eligibility and role-based assignment authority.
    """
    from accounts.models import User

    if assignee:
        if not assignee.is_active:
            raise ValidationError("Inactive users cannot be assigned tasks.")
        if assignee.role == User.Roles.CLIENT:
            raise ValidationError("Clients cannot be assigned tasks.")
        validate_assignee_project_membership(task, assignee)

    if task and task.status == TaskStatus.COMPLETED:
        raise ValidationError("Completed tasks cannot be reassigned.")

    if actor is None:
        return

    if actor.role == User.Roles.ADMIN:
        return

    if actor.role == User.Roles.MANAGER:
        is_managed = (
            task.project.manager_id == actor.id or
            task.project.created_by_id == actor.id
        )
        if is_managed:
            return
        raise ValidationError("Managers can only assign tasks in their own projects.")

    if actor.role == User.Roles.DEVELOPER:
        current_assignee_id = getattr(task, 'assigned_to_id', None)
        is_self_assignment = assignee and assignee.id == actor.id
        is_self_unassignment = assignee is None and current_assignee_id == actor.id
        if is_self_assignment or is_self_unassignment:
            return
        raise ValidationError("Developers can only assign or unassign themselves.")

    raise ValidationError("You are not authorized to assign tasks.")

def validate_attachment_file(uploaded_file):
    """
    Validates file size (max 10MB) and allowed extensions and MIME types.
    """
    max_size = 10 * 1024 * 1024  # 10MB
    if uploaded_file.size > max_size:
        raise ValidationError(
            f"File size exceeds the maximum limit of 10MB "
            f"(current size: {uploaded_file.size / (1024*1024):.2f}MB)."
        )

    filename = uploaded_file.name
    ext = os.path.splitext(filename)[1].lower().lstrip('.')

    allowed_extensions = {
        'png', 'jpg', 'jpeg', 'gif', 'webp',
        'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
        'txt', 'csv', 'zip', 'tar', 'gz'
    }

    if not ext or ext not in allowed_extensions:
        raise ValidationError(
            f"File extension '.{ext}' is not allowed. "
            f"Supported formats: {', '.join(sorted(allowed_extensions))}"
        )

    content_type = getattr(uploaded_file, 'content_type', None)
    if not content_type:
        content_type, _ = mimetypes.guess_type(filename)
    if not content_type:
        content_type = 'application/octet-stream'

    allowed_mime_types = {
        'image/png', 'image/jpeg', 'image/gif', 'image/webp',
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-powerpoint',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'text/plain', 'text/csv',
        'application/zip', 'application/x-zip-compressed',
        'application/x-tar', 'application/gzip', 'application/x-gzip',
    }

    if content_type not in allowed_mime_types:
        raise ValidationError(f"MIME type '{content_type}' is not allowed.")
