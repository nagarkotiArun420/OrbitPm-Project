import logging
from django.conf import settings
from common.models import ActivityLog
from common.utils import get_client_ip
from common.constants import ActionType, TargetType

logger = logging.getLogger(__name__)

def log_activity(
    actor=None,
    action_type=None,
    target_type=None,
    target_id=None,
    target_repr=None,
    description="",
    metadata=None,
    ip_address=None,
    request=None
):
    """
    Creates an ActivityLog entry in the database.
    Can extract actor and ip_address directly from the request object if passed.
    """
    if metadata is None:
        metadata = {}
        
    if request:
        if not actor and request.user and request.user.is_authenticated:
            actor = request.user
        if not ip_address:
            ip_address = get_client_ip(request)
            
    try:
        activity = ActivityLog.objects.create(
            actor=actor,
            action_type=action_type,
            target_type=target_type,
            target_id=str(target_id) if target_id else None,
            target_repr=target_repr,
            description=description,
            metadata=metadata,
            ip_address=ip_address
        )
        return activity
    except Exception as e:
        # Fallback to logger warning to prevent audit crashes from failing primary business transactions
        logger.error(f"Failed to create activity log: {e}", exc_info=True)
        return None

def log_project_activity(
    actor=None,
    project=None,
    action_type=None,
    description="",
    metadata=None,
    ip_address=None,
    request=None
):
    """
    Helper service to log activities relating to Project operations.
    """
    if project is None:
        return None
    return log_activity(
        actor=actor,
        action_type=action_type,
        target_type=TargetType.PROJECT,
        target_id=project.id,
        target_repr=project.title,
        description=description,
        metadata=metadata,
        ip_address=ip_address,
        request=request
    )

def log_task_activity(
    actor=None,
    task=None,
    action_type=None,
    description="",
    metadata=None,
    ip_address=None,
    request=None
):
    """
    Helper service to log activities relating to Task operations.
    """
    if task is None:
        return None
    return log_activity(
        actor=actor,
        action_type=action_type,
        target_type=TargetType.TASK,
        target_id=task.id,
        target_repr=task.title,
        description=description,
        metadata=metadata,
        ip_address=ip_address,
        request=request
    )
