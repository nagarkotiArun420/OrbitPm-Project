from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from projects.models import Project, ProjectMember, ProjectInvitation
from projects.constants import ProjectInvitationStatus, ProjectMemberRole
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


def get_invitation_expiry():
    """
    Returns the default project invitation expiry timestamp.
    """
    days = getattr(settings, 'PROJECT_INVITATION_EXPIRY_DAYS', 7)
    return timezone.now() + timedelta(days=days)


def _expire_invitation_if_needed(invitation, request=None):
    if not invitation.is_expired:
        return False

    invitation.status = ProjectInvitationStatus.EXPIRED
    invitation.save(update_fields=['status'])
    log_activity(
        actor=None,
        action_type=ActionType.INVITATION_EXPIRED,
        target_type=TargetType.PROJECT_INVITATION,
        target_id=invitation.id,
        target_repr=f"{invitation.invited_user.email} -> {invitation.project.title}",
        description=f"Invitation for {invitation.invited_user.email} to project '{invitation.project.title}' expired.",
        metadata={
            'project_id': str(invitation.project_id),
            'invited_user_id': str(invitation.invited_user_id),
        },
        request=request,
    )
    return True


def _sync_membership_for_invitation(invitation):
    member, _ = ProjectMember.objects.update_or_create(
        project=invitation.project,
        user=invitation.invited_user,
        defaults={
            'role': invitation.role,
            'invited_by': invitation.invited_by,
            'is_active': True,
        },
    )

    if invitation.role in (ProjectMemberRole.DEVELOPER, ProjectMemberRole.VIEWER):
        invitation.project.team_members.add(invitation.invited_user)
    else:
        invitation.project.team_members.remove(invitation.invited_user)

    return member


def _validate_invitation_token(invitation, token=None):
    if token and token != invitation.token:
        raise ValidationError({'token': 'Invalid invitation token.'})


@transaction.atomic
def create_invitation(project, invited_user, role, invited_by, request=None, expires_at=None):
    """
    Create a project invitation with duplicate/member validation,
    activity logging, and in-app notification delivery.
    """
    role = role or ProjectMemberRole.DEVELOPER

    if not invited_user.is_active:
        raise ValidationError({'invited_user_id': 'Inactive users cannot receive project invitations.'})

    if ProjectMember.objects.filter(project=project, user=invited_user).exists():
        raise ValidationError({'invited_user_id': 'Existing project members cannot be reinvited.'})

    ProjectInvitation.objects.filter(
        project=project,
        invited_user=invited_user,
        status=ProjectInvitationStatus.PENDING,
        expires_at__lte=timezone.now(),
    ).update(status=ProjectInvitationStatus.EXPIRED)

    if ProjectInvitation.objects.filter(
        project=project,
        invited_user=invited_user,
        status=ProjectInvitationStatus.PENDING,
    ).exists():
        raise ValidationError({'invited_user_id': 'A pending invitation already exists for this user.'})

    invitation = ProjectInvitation(
        project=project,
        invited_user=invited_user,
        invited_by=invited_by,
        role=role,
        expires_at=expires_at or get_invitation_expiry(),
    )
    invitation.save()

    log_activity(
        actor=invited_by,
        action_type=ActionType.INVITATION_SENT,
        target_type=TargetType.PROJECT_INVITATION,
        target_id=invitation.id,
        target_repr=f"{invited_user.email} -> {project.title}",
        description=f"{invited_user.email} was invited to project '{project.title}' as {role}.",
        metadata={
            'project_id': str(project.id),
            'invited_user_id': str(invited_user.id),
            'role': role,
            'expires_at': invitation.expires_at.isoformat(),
        },
        request=request,
    )

    send_in_app_notification(
        recipient=invited_user,
        title='Project Invitation',
        message=f"You have been invited to project '{project.title}' as {invitation.get_role_display()}.",
        notification_type=NotificationType.PROJECT_INVITATION_SENT,
        actor=invited_by,
        metadata={
            'project_id': str(project.id),
            'project_title': project.title,
            'invitation_id': str(invitation.id),
            'role': role,
            'expires_at': invitation.expires_at.isoformat(),
        },
    )

    return invitation


def accept_invitation(invitation, actor, token=None, request=None):
    """
    Accept an invitation and convert it into an active ProjectMember row.
    """
    expired = False
    with transaction.atomic():
        invitation = ProjectInvitation.objects.select_for_update().select_related(
            'project',
            'invited_user',
            'invited_by',
        ).get(pk=invitation.pk)
        _validate_invitation_token(invitation, token)

        if actor.role != User.Roles.ADMIN and invitation.invited_user_id != actor.id:
            raise ValidationError({'invitation': 'Only the invited user can accept this invitation.'})

        if invitation.status != ProjectInvitationStatus.PENDING:
            raise ValidationError({'status': f'Only pending invitations can be accepted. Current status: {invitation.status}.'})

        if _expire_invitation_if_needed(invitation, request=request):
            expired = True
        else:
            member = _sync_membership_for_invitation(invitation)
            invitation.status = ProjectInvitationStatus.ACCEPTED
            invitation.accepted_at = timezone.now()
            invitation.save(update_fields=['status', 'accepted_at'])

            log_activity(
                actor=actor,
                action_type=ActionType.INVITATION_ACCEPTED,
                target_type=TargetType.PROJECT_INVITATION,
                target_id=invitation.id,
                target_repr=f"{invitation.invited_user.email} -> {invitation.project.title}",
                description=f"{invitation.invited_user.email} accepted the invitation to project '{invitation.project.title}'.",
                metadata={
                    'project_id': str(invitation.project_id),
                    'member_id': str(member.id),
                    'role': invitation.role,
                },
                request=request,
            )

            if invitation.invited_by:
                send_in_app_notification(
                    recipient=invitation.invited_by,
                    title='Project Invitation Accepted',
                    message=f"{invitation.invited_user.full_name} accepted the invitation to '{invitation.project.title}'.",
                    notification_type=NotificationType.PROJECT_INVITATION_ACCEPTED,
                    actor=actor,
                    metadata={
                        'project_id': str(invitation.project_id),
                        'project_title': invitation.project.title,
                        'invitation_id': str(invitation.id),
                        'member_id': str(member.id),
                    },
                )

    if expired:
        raise ValidationError({'status': 'Expired invitations cannot be accepted.'})

    return invitation


def decline_invitation(invitation, actor, token=None, request=None):
    """
    Decline a pending invitation.
    """
    expired = False
    with transaction.atomic():
        invitation = ProjectInvitation.objects.select_for_update().select_related(
            'project',
            'invited_user',
            'invited_by',
        ).get(pk=invitation.pk)
        _validate_invitation_token(invitation, token)

        if actor.role != User.Roles.ADMIN and invitation.invited_user_id != actor.id:
            raise ValidationError({'invitation': 'Only the invited user can decline this invitation.'})

        if invitation.status != ProjectInvitationStatus.PENDING:
            raise ValidationError({'status': f'Only pending invitations can be declined. Current status: {invitation.status}.'})

        if _expire_invitation_if_needed(invitation, request=request):
            expired = True
        else:
            invitation.status = ProjectInvitationStatus.DECLINED
            invitation.save(update_fields=['status'])

            log_activity(
                actor=actor,
                action_type=ActionType.INVITATION_DECLINED,
                target_type=TargetType.PROJECT_INVITATION,
                target_id=invitation.id,
                target_repr=f"{invitation.invited_user.email} -> {invitation.project.title}",
                description=f"{invitation.invited_user.email} declined the invitation to project '{invitation.project.title}'.",
                metadata={
                    'project_id': str(invitation.project_id),
                    'invited_user_id': str(invitation.invited_user_id),
                    'role': invitation.role,
                },
                request=request,
            )

            if invitation.invited_by:
                send_in_app_notification(
                    recipient=invitation.invited_by,
                    title='Project Invitation Declined',
                    message=f"{invitation.invited_user.full_name} declined the invitation to '{invitation.project.title}'.",
                    notification_type=NotificationType.PROJECT_INVITATION_DECLINED,
                    actor=actor,
                    metadata={
                        'project_id': str(invitation.project_id),
                        'project_title': invitation.project.title,
                        'invitation_id': str(invitation.id),
                    },
                )

    if expired:
        raise ValidationError({'status': 'Expired invitations cannot be declined.'})

    return invitation


@transaction.atomic
def revoke_invitation(invitation, actor, request=None):
    """
    Revoke a pending invitation by marking it expired.
    """
    invitation = ProjectInvitation.objects.select_for_update().select_related(
        'project',
        'invited_user',
    ).get(pk=invitation.pk)

    if invitation.status != ProjectInvitationStatus.PENDING:
        raise ValidationError({'status': f'Only pending invitations can be revoked. Current status: {invitation.status}.'})

    invitation.status = ProjectInvitationStatus.EXPIRED
    invitation.save(update_fields=['status'])

    log_activity(
        actor=actor,
        action_type=ActionType.INVITATION_REVOKED,
        target_type=TargetType.PROJECT_INVITATION,
        target_id=invitation.id,
        target_repr=f"{invitation.invited_user.email} -> {invitation.project.title}",
        description=f"Invitation for {invitation.invited_user.email} to project '{invitation.project.title}' was revoked.",
        metadata={
            'project_id': str(invitation.project_id),
            'invited_user_id': str(invitation.invited_user_id),
            'role': invitation.role,
        },
        request=request,
    )

    send_in_app_notification(
        recipient=invitation.invited_user,
        title='Project Invitation Revoked',
        message=f"Your invitation to project '{invitation.project.title}' has been revoked.",
        notification_type=NotificationType.PROJECT_INVITATION_REVOKED,
        actor=actor,
        metadata={
            'project_id': str(invitation.project_id),
            'project_title': invitation.project.title,
            'invitation_id': str(invitation.id),
        },
    )

    return invitation


@transaction.atomic
def expire_invitation(invitation, request=None):
    """
    Expire a pending invitation if its expiry timestamp has passed.
    """
    invitation = ProjectInvitation.objects.select_for_update().select_related(
        'project',
        'invited_user',
    ).get(pk=invitation.pk)
    _expire_invitation_if_needed(invitation, request=request)
    return invitation


