from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from common.constants import ActionType, TargetType
from common.models import ActivityLog
from notifications.constants import NotificationType
from notifications.models import Notification
from projects.constants import (
    ProjectInvitationStatus,
    ProjectMemberRole,
    ProjectPriority,
    ProjectStatus,
)
from projects.models import Project, ProjectInvitation, ProjectMember

User = get_user_model()


class ProjectInvitationAPITests(APITestCase):
    """
    Tests for /api/v1/projects/{slug}/invitations/ workflow endpoints.
    """
    def setUp(self):
        self.admin = User.objects.create_user(
            email='admin@orbitpm.com',
            password='pass123',
            full_name='Admin User',
            role=User.Roles.ADMIN,
        )
        self.manager = User.objects.create_user(
            email='manager@orbitpm.com',
            password='pass123',
            full_name='Manager User',
            role=User.Roles.MANAGER,
        )
        self.other_manager = User.objects.create_user(
            email='other-manager@orbitpm.com',
            password='pass123',
            full_name='Other Manager',
            role=User.Roles.MANAGER,
        )
        self.developer = User.objects.create_user(
            email='dev@orbitpm.com',
            password='pass123',
            full_name='Developer User',
            role=User.Roles.DEVELOPER,
        )
        self.invited_user = User.objects.create_user(
            email='invitee@orbitpm.com',
            password='pass123',
            full_name='Invited User',
            role=User.Roles.DEVELOPER,
        )
        self.inactive_user = User.objects.create_user(
            email='inactive@orbitpm.com',
            password='pass123',
            full_name='Inactive User',
            role=User.Roles.DEVELOPER,
            is_active=False,
        )

        self.project = Project.objects.create(
            title='Invitation Workflow Project',
            status=ProjectStatus.IN_PROGRESS,
            priority=ProjectPriority.HIGH,
            manager=self.manager,
            created_by=self.manager,
        )
        self.project.team_members.add(self.developer)

        self.other_project = Project.objects.create(
            title='Other Invitation Project',
            status=ProjectStatus.PLANNING,
            manager=self.other_manager,
            created_by=self.other_manager,
        )

        self.list_url = reverse(
            'project-invitation-list',
            kwargs={'project_slug': self.project.slug},
        )

    def detail_url(self, invitation):
        return reverse(
            'project-invitation-detail',
            kwargs={'project_slug': self.project.slug, 'pk': invitation.pk},
        )

    def accept_url(self, invitation):
        return reverse(
            'project-invitation-accept',
            kwargs={'project_slug': self.project.slug, 'pk': invitation.pk},
        )

    def decline_url(self, invitation):
        return reverse(
            'project-invitation-decline',
            kwargs={'project_slug': self.project.slug, 'pk': invitation.pk},
        )

    def revoke_url(self, invitation):
        return reverse(
            'project-invitation-revoke',
            kwargs={'project_slug': self.project.slug, 'pk': invitation.pk},
        )

    def create_invitation(self, **overrides):
        data = {
            'project': self.project,
            'invited_user': self.invited_user,
            'invited_by': self.manager,
            'role': ProjectMemberRole.DEVELOPER,
            'expires_at': timezone.now() + timedelta(days=7),
        }
        data.update(overrides)
        return ProjectInvitation.objects.create(**data)

    def test_manager_can_create_invitation_with_token_notification_and_activity(self):
        self.client.force_authenticate(user=self.manager)
        payload = {
            'invited_user_id': str(self.invited_user.id),
            'role': ProjectMemberRole.DEVELOPER,
        }

        response = self.client.post(self.list_url, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.data['data']
        invitation = ProjectInvitation.objects.get(id=data['id'])
        self.assertEqual(invitation.status, ProjectInvitationStatus.PENDING)
        self.assertTrue(invitation.token)
        self.assertEqual(data['token'], invitation.token)
        self.assertTrue(Notification.objects.filter(
            recipient=self.invited_user,
            notification_type=NotificationType.PROJECT_INVITATION_SENT,
        ).exists())
        self.assertTrue(ActivityLog.objects.filter(
            action_type=ActionType.INVITATION_SENT,
            target_type=TargetType.PROJECT_INVITATION,
            target_id=str(invitation.id),
        ).exists())

    def test_duplicate_existing_member_and_inactive_invites_are_rejected(self):
        self.create_invitation()
        self.client.force_authenticate(user=self.manager)

        duplicate_response = self.client.post(self.list_url, {
            'invited_user_id': str(self.invited_user.id),
            'role': ProjectMemberRole.VIEWER,
        })
        self.assertEqual(duplicate_response.status_code, status.HTTP_400_BAD_REQUEST)

        ProjectMember.objects.create(
            project=self.project,
            user=self.developer,
            role=ProjectMemberRole.DEVELOPER,
            invited_by=self.manager,
        )
        member_response = self.client.post(self.list_url, {
            'invited_user_id': str(self.developer.id),
            'role': ProjectMemberRole.DEVELOPER,
        })
        self.assertEqual(member_response.status_code, status.HTTP_400_BAD_REQUEST)

        inactive_response = self.client.post(self.list_url, {
            'invited_user_id': str(self.inactive_user.id),
            'role': ProjectMemberRole.DEVELOPER,
        })
        self.assertEqual(inactive_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invited_user_can_accept_invitation_and_membership_is_created(self):
        invitation = self.create_invitation()
        self.client.force_authenticate(user=self.invited_user)

        response = self.client.post(self.accept_url(invitation), {
            'token': invitation.token,
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, ProjectInvitationStatus.ACCEPTED)
        self.assertIsNotNone(invitation.accepted_at)
        self.assertTrue(ProjectMember.objects.filter(
            project=self.project,
            user=self.invited_user,
            role=ProjectMemberRole.DEVELOPER,
            is_active=True,
        ).exists())
        self.assertIn(self.invited_user, self.project.team_members.all())
        self.assertTrue(Notification.objects.filter(
            recipient=self.manager,
            notification_type=NotificationType.PROJECT_INVITATION_ACCEPTED,
        ).exists())

    def test_expired_invitation_cannot_be_accepted(self):
        invitation = self.create_invitation(
            expires_at=timezone.now() - timedelta(days=1),
        )
        self.client.force_authenticate(user=self.invited_user)

        response = self.client.post(self.accept_url(invitation), {
            'token': invitation.token,
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, ProjectInvitationStatus.EXPIRED)
        self.assertFalse(ProjectMember.objects.filter(
            project=self.project,
            user=self.invited_user,
        ).exists())

    def test_invited_user_can_decline_invitation(self):
        invitation = self.create_invitation()
        self.client.force_authenticate(user=self.invited_user)

        response = self.client.post(self.decline_url(invitation), {
            'token': invitation.token,
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, ProjectInvitationStatus.DECLINED)
        self.assertTrue(Notification.objects.filter(
            recipient=self.manager,
            notification_type=NotificationType.PROJECT_INVITATION_DECLINED,
        ).exists())
        self.assertTrue(ActivityLog.objects.filter(
            action_type=ActionType.INVITATION_DECLINED,
            target_id=str(invitation.id),
        ).exists())

    def test_manager_can_revoke_pending_invitation(self):
        invitation = self.create_invitation()
        self.client.force_authenticate(user=self.manager)

        response = self.client.post(self.revoke_url(invitation))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, ProjectInvitationStatus.EXPIRED)
        self.assertTrue(Notification.objects.filter(
            recipient=self.invited_user,
            notification_type=NotificationType.PROJECT_INVITATION_REVOKED,
        ).exists())
        self.assertTrue(ActivityLog.objects.filter(
            action_type=ActionType.INVITATION_REVOKED,
            target_id=str(invitation.id),
        ).exists())

    def test_project_permissions_are_enforced_for_invitation_management(self):
        self.client.force_authenticate(user=self.developer)
        create_response = self.client.post(self.list_url, {
            'invited_user_id': str(self.invited_user.id),
            'role': ProjectMemberRole.DEVELOPER,
        })
        self.assertEqual(create_response.status_code, status.HTTP_403_FORBIDDEN)

        list_response = self.client.get(self.list_url)
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)

        other_url = reverse(
            'project-invitation-list',
            kwargs={'project_slug': self.other_project.slug},
        )
        self.client.force_authenticate(user=self.manager)
        other_response = self.client.post(other_url, {
            'invited_user_id': str(self.invited_user.id),
            'role': ProjectMemberRole.DEVELOPER,
        })
        self.assertEqual(other_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_wrong_token_cannot_accept_invitation(self):
        invitation = self.create_invitation()
        self.client.force_authenticate(user=self.invited_user)

        response = self.client.post(self.accept_url(invitation), {
            'token': 'not-the-token',
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, ProjectInvitationStatus.PENDING)
