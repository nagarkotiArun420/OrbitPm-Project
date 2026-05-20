from django.db import transaction
from projects.models import Project
from common.services import log_project_activity
from common.constants import ActionType
from common.utils import get_model_changes
from notifications.services import notify_project_update


@transaction.atomic
def update_project(project, request=None, **validated_data):
    """
    Service layer method to safely update a Project.
    Synchronizes attributes and handles M2M team updates under transactions.
    """
    changes = get_model_changes(project, validated_data)
    team_members = validated_data.pop('team_members', None)

    # Update baseline attributes
    for field, value in validated_data.items():
        setattr(project, field, value)

    project.save()

    # Handle team members update
    if team_members is not None:
        old_members = list(project.team_members.values_list('email', flat=True))
        project.team_members.set(team_members)
        new_members = list(project.team_members.values_list('email', flat=True))

        if set(old_members) != set(new_members):
            changes['team_members'] = {
                'old': old_members,
                'new': new_members
            }

    # If any changes exist, log activity + notify
    if changes:

        # Decide action type
        if len(changes) == 1 and 'status' in changes:
            action_type = ActionType.STATUS_CHANGED
            description = (
                f"Project '{project.title}' status changed from "
                f"{changes['status']['old']} to {changes['status']['new']}."
            )
        else:
            action_type = ActionType.UPDATED
            description = f"Project '{project.title}' was updated."

        # Log activity
        log_project_activity(
            actor=request.user if request else None,
            project=project,
            action_type=action_type,
            description=description,
            metadata={'changes': changes},
            request=request
        )

        # Send notification
        actor = request.user if request else None
        notify_project_update(
            project,
            actor=actor,
            changes=changes,
            request=request
        )

    return project