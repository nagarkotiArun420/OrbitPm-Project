from django.db import transaction
from projects.models import Project
from common.services import log_project_activity
from common.constants import ActionType
from common.utils import get_model_changes

@transaction.atomic
def create_project(created_by, request=None, **validated_data):
    """
    Service layer method to safely create a Project.
    Encapsulates audit tagging, slug generation, and M2M assignments.
    """
    team_members = validated_data.pop('team_members', [])
    
    # Instantiate the Project with attributes
    project = Project(
        created_by=created_by,
        **validated_data
    )
    # Triggers clean() validation and unique slug resolution on save
    project.save()
    
    # Assign M2M relations after saving the main model
    if team_members:
        project.team_members.set(team_members)
        
    log_project_activity(
        actor=created_by,
        project=project,
        action_type=ActionType.CREATED,
        description=f"Project '{project.title}' was created.",
        request=request
    )
        
    return project


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
    
    # If team members are supplied in update payload, override current members
    if team_members is not None:
        old_members = list(project.team_members.values_list('email', flat=True))
        project.team_members.set(team_members)
        new_members = list(project.team_members.values_list('email', flat=True))
        if set(old_members) != set(new_members):
            changes['team_members'] = {
                'old': old_members,
                'new': new_members
            }
        
    if changes:
        if len(changes) == 1 and 'status' in changes:
            action_type = ActionType.STATUS_CHANGED
            description = f"Project '{project.title}' status changed from {changes['status']['old']} to {changes['status']['new']}."
        else:
            action_type = ActionType.UPDATED
            description = f"Project '{project.title}' was updated."
            
        log_project_activity(
            actor=request.user if request else None,
            project=project,
            action_type=action_type,
            description=description,
            metadata={'changes': changes},
            request=request
        )
        
        from notifications.services import notify_project_update
        actor = request.user if request else None
        notify_project_update(project, actor=actor, changes=changes, request=request)
        
    return project


@transaction.atomic
def delete_project(project, request=None):
    """
    Service layer method to safely delete a Project.
    Ensures safe operations.
    """
    log_project_activity(
        actor=request.user if request else None,
        project=project,
        action_type=ActionType.DELETED,
        description=f"Project '{project.title}' was deleted.",
        request=request
    )
    project.delete()

