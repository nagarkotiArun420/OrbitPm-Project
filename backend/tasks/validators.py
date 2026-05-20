from django.core.exceptions import ValidationError
from tasks.constants import TaskStatus
import os
import mimetypes


# ─────────────────────────────────────────────
# STATUS TRANSITION MATRIX
# ─────────────────────────────────────────────
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


def validate_status_transition(current_status, new_status):
    if current_status == new_status:
        return

    allowed = ALLOWED_TRANSITIONS.get(current_status, [])

    if new_status not in allowed:
        allowed_labels = [dict(TaskStatus.choices).get(s, s) for s in allowed]

        raise ValidationError(
            f"Invalid status transition from '{current_status}' to '{new_status}'. "
            f"Allowed transitions: {', '.join(allowed_labels) or 'none'}."
        )


def get_valid_next_statuses(current_status):
    return ALLOWED_TRANSITIONS.get(current_status, [])


def validate_due_date_within_project(due_date, project):
    if not due_date or not project:
        return

    if project.start_date and due_date < project.start_date:
        raise ValidationError(
            f"Due date cannot be before project start date ({project.start_date})."
        )

    if project.deadline and due_date > project.deadline:
        raise ValidationError(
            f"Due date cannot be after project deadline ({project.deadline})."
        )


def validate_assignee_project_membership(user, project):
    if not user or not project:
        return

    is_member = (
        project.team_members.filter(id=user.id).exists()
        or project.manager == user
        or project.created_by == user
    )

    if not is_member:
        raise ValidationError("User must be a member of the project team.")


def validate_task_assignment(task, new_assignee, actor):
    from accounts.models import User

    current_assignee = task.assigned_to if task.pk else None

    # completed tasks cannot be reassigned
    if task.pk and task.status == TaskStatus.COMPLETED and current_assignee != new_assignee:
        raise ValidationError("Completed tasks cannot be reassigned.")

    if new_assignee:
        if not new_assignee.is_active:
            raise ValidationError("Inactive users cannot be assigned tasks.")

        if new_assignee.role == User.Roles.CLIENT:
            raise ValidationError("Clients cannot be assigned tasks.")

        validate_assignee_project_membership(new_assignee, task.project)

    if current_assignee != new_assignee:
        if not actor:
            raise ValidationError("Actor is required for assignment validation.")

        if actor.role == User.Roles.ADMIN:
            return

        if actor.role == User.Roles.MANAGER:
            if not (
                task.project.manager == actor
                or task.project.created_by == actor
            ):
                raise ValidationError("Managers can only assign tasks in their projects.")

        elif actor.role == User.Roles.DEVELOPER:
            if new_assignee is not None and new_assignee != actor:
                raise ValidationError("Developers cannot assign tasks to others.")

        elif actor.role == User.Roles.CLIENT:
            raise ValidationError("Clients cannot assign tasks.")

        else:
            raise ValidationError("Unauthorized role for task assignment.")


def validate_attachment_file(uploaded_file):
    max_size = 10 * 1024 * 1024  # 10MB

    if uploaded_file.size > max_size:
        raise ValidationError(
            f"File exceeds 10MB limit (current: {uploaded_file.size / (1024*1024):.2f}MB)"
        )

    filename = uploaded_file.name
    ext = os.path.splitext(filename)[1].lower().lstrip('.')

    allowed_extensions = {
        'png', 'jpg', 'jpeg', 'gif', 'webp',
        'pdf', 'doc', 'docx', 'xls', 'xlsx',
        'ppt', 'pptx', 'txt', 'csv',
        'zip', 'tar', 'gz'
    }

    if ext not in allowed_extensions:
        raise ValidationError(f"Extension .{ext} is not allowed.")

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
        'application/x-tar', 'application/gzip'
    }

    if content_type not in allowed_mime_types:
        raise ValidationError(f"MIME type '{content_type}' is not allowed.")