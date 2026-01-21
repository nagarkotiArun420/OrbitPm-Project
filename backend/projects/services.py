from django.db import transaction
from projects.models import Project, ProjectMember
from projects.constants import ProjectMemberRole
from common.services import log_project_activity, log_activity
from common.constants import ActionType, TargetType
from common.utils import get_model_changes
from notifications.services import send_in_app_notification
from notifications.constants import NotificationType

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


@transaction.atomic
def add_project_member(project, user, role, invited_by=None, request=None):
    """
    Service layer method to add a user as a project member.
    Enforces business rules, syncs M2M relations, logs activity, and sends notification.
    """
    member = ProjectMember(
        project=project,
        user=user,
        role=role,
        invited_by=invited_by
    )
    member.full_clean()
    member.save()

    # Sync legacy M2M team_members for backward-compatible role isolation
    if role in (ProjectMemberRole.DEVELOPER, ProjectMemberRole.VIEWER):
        project.team_members.add(user)

    log_activity(
        actor=invited_by,
        action_type=ActionType.MEMBER_ADDED,
        target_type=TargetType.PROJECT_MEMBER,
        target_id=str(member.id),
        target_repr=f"{user.email} as {role} on {project.title}",
        description=f"{user.email} was added to project '{project.title}' as {role}.",
        metadata={'project_id': str(project.id), 'role': role},
        request=request
    )

    send_in_app_notification(
        recipient=user,
        title='Added to Project',
        message=f"You have been added to project '{project.title}' as {member.get_role_display()}.",
        notification_type=NotificationType.MEMBER_ADDED,
        actor=invited_by,
        metadata={'project_id': str(project.id), 'project_title': project.title, 'role': role}
    )

    return member


@transaction.atomic
def update_member_role(member, new_role, updated_by=None, request=None):
    """
    Service layer method to update a project member's role.
    Syncs M2M relations, logs activity, and sends notification.
    """
    old_role = member.role
    member.role = new_role
    member.save(update_fields=['role'])

    project = member.project
    user = member.user

    # Sync legacy M2M team_members
    if new_role in (ProjectMemberRole.DEVELOPER, ProjectMemberRole.VIEWER):
        project.team_members.add(user)
    else:
        project.team_members.remove(user)

    log_activity(
        actor=updated_by,
        action_type=ActionType.MEMBER_ROLE_UPDATED,
        target_type=TargetType.PROJECT_MEMBER,
        target_id=str(member.id),
        target_repr=f"{user.email} on {project.title}",
        description=f"{user.email} role updated from {old_role} to {new_role} on project '{project.title}'.",
        metadata={
            'project_id': str(project.id),
            'old_role': old_role,
            'new_role': new_role
        },
        request=request
    )

    send_in_app_notification(
        recipient=user,
        title='Project Role Updated',
        message=f"Your role on project '{project.title}' has been updated from {old_role} to {member.get_role_display()}.",
        notification_type=NotificationType.MEMBER_ROLE_UPDATED,
        actor=updated_by,
        metadata={'project_id': str(project.id), 'project_title': project.title, 'old_role': old_role, 'new_role': new_role}
    )

    return member


@transaction.atomic
def remove_project_member(member, removed_by=None, request=None):
    """
    Service layer method to remove a project member.
    Cleans up M2M relations, logs activity, sends notification, and deletes the record.
    """
    project = member.project
    user = member.user
    role = member.role

    # Remove from legacy M2M team_members
    project.team_members.remove(user)

    log_activity(
        actor=removed_by,
        action_type=ActionType.MEMBER_REMOVED,
        target_type=TargetType.PROJECT_MEMBER,
        target_id=str(member.id),
        target_repr=f"{user.email} from {project.title}",
        description=f"{user.email} was removed from project '{project.title}' (was {role}).",
        metadata={'project_id': str(project.id), 'role': role},
        request=request
    )

    send_in_app_notification(
        recipient=user,
        title='Removed from Project',
        message=f"You have been removed from project '{project.title}'.",
        notification_type=NotificationType.MEMBER_REMOVED,
        actor=removed_by,
        metadata={'project_id': str(project.id), 'project_title': project.title}
    )

    member.delete()


