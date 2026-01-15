from django.core.exceptions import ValidationError
from tasks.constants import TaskStatus
import os
import mimetypes

# ... (all existing code unchanged above) ...

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