from unittest.mock import patch
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from projects.models import Project, ProjectMember
from projects.constants import ProjectStatus, ProjectPriority, ProjectMemberRole

User = get_user_model()


class ProjectMemberAPITests(APITestCase):
    """
    Comprehensive tests for the ProjectMember management endpoints:
    /api/v1/projects/{slug}/members/
    """

    def setUp(self):
        # ---- Users ----
        self.admin = User.objects.create_user(
            email='admin@orbitpm.com', password='pass123',
            full_name='Admin User', role=User.Roles.ADMIN
        )
        self.manager = User.objects.create_user(
            email='manager@orbitpm.com', password='pass123',
            full_name='Manager User', role=User.Roles.MANAGER
        )
        self.manager_other = User.objects.create_user(
            email='manager2@orbitpm.com', password='pass123',
            full_name='Other Manager', role=User.Roles.MANAGER
        )
        self.developer = User.objects.create_user(
            email='dev@orbitpm.com', password='pass123',
            full_name='Developer User', role=User.Roles.DEVELOPER
        )
        self.developer2 = User.objects.create_user(
            email='dev2@orbitpm.com', password='pass123',
            full_name='Developer Two', role=User.Roles.DEVELOPER
        )
        self.client_user = User.objects.create_user(
            email='client@orbitpm.com', password='pass123',
            full_name='Client User', role=User.Roles.CLIENT
        )
        self.inactive_user = User.objects.create_user(
            email='inactive@orbitpm.com', password='pass123',
            full_name='Inactive User', role=User.Roles.DEVELOPER,
            is_active=False
        )

        # ---- Project managed by self.manager ----
        self.project = Project.objects.create(
            title='Membership Test Project',
            description='Project for membership tests',
            status=ProjectStatus.IN_PROGRESS,
            priority=ProjectPriority.HIGH,
            start_date=timezone.localdate(),
            deadline=timezone.localdate() + timedelta(days=30),
            budget=Decimal('15000.00'),
            manager=self.manager,
            client=self.client_user,
            created_by=self.manager
        )
        self.project.team_members.add(self.developer)

        # ---- Unrelated project managed by manager_other ----
        self.other_project = Project.objects.create(
            title='Other Team Project',
            status=ProjectStatus.PLANNING,
            manager=self.manager_other,
            created_by=self.manager_other
        )

        # ---- URLs ----
        self.list_url = reverse(
            'project-member-list',
            kwargs={'project_slug': self.project.slug}
        )

    def detail_url(self, member_pk):
        return reverse(
            'project-member-detail',
            kwargs={
                'project_slug': self.project.slug,
                'pk': str(member_pk)
            }
        )

    # ==========================================================
    # 1. ADD MEMBER (POST)
    # ==========================================================
    @patch('projects.services.send_in_app_notification')
    @patch('projects.services.log_activity')
    def test_admin_can_add_member(self, mock_log, mock_notify):
        self.client.force_authenticate(user=self.admin)
        payload = {'user_id': str(self.developer2.id), 'role': 'DEVELOPER'}
        response = self.client.post(self.list_url, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json().get('data', response.json())
        self.assertEqual(data['role'], 'DEVELOPER')
        self.assertTrue(ProjectMember.objects.filter(
            project=self.project, user=self.developer2
        ).exists())
        mock_log.assert_called_once()
        mock_notify.assert_called_once()

    @patch('projects.services.send_in_app_notification')
    @patch('projects.services.log_activity')
    def test_manager_can_add_member_to_own_project(self, mock_log, mock_notify):
        self.client.force_authenticate(user=self.manager)
        payload = {'user_id': str(self.developer2.id), 'role': 'DEVELOPER'}
        response = self.client.post(self.list_url, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_manager_cannot_add_member_to_unrelated_project(self):
        url = reverse(
            'project-member-list',
            kwargs={'project_slug': self.other_project.slug}
        )
        self.client.force_authenticate(user=self.manager)
        payload = {'user_id': str(self.developer2.id), 'role': 'DEVELOPER'}
        response = self.client.post(url, payload)
        self.assertIn(response.status_code, [
            status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND
        ])

    def test_developer_cannot_add_member(self):
        self.client.force_authenticate(user=self.developer)
        payload = {'user_id': str(self.developer2.id), 'role': 'DEVELOPER'}
        response = self.client.post(self.list_url, payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_client_cannot_add_member(self):
        self.client.force_authenticate(user=self.client_user)
        payload = {'user_id': str(self.developer2.id), 'role': 'DEVELOPER'}
        response = self.client.post(self.list_url, payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ==========================================================
    # 2. DUPLICATE MEMBERSHIP REJECTION
    # ==========================================================
    @patch('projects.services.send_in_app_notification')
    @patch('projects.services.log_activity')
    def test_duplicate_membership_rejected(self, mock_log, mock_notify):
        # First add the member
        ProjectMember.objects.create(
            project=self.project, user=self.developer2,
            role=ProjectMemberRole.DEVELOPER, invited_by=self.admin
        )
        self.client.force_authenticate(user=self.admin)
        payload = {'user_id': str(self.developer2.id), 'role': 'VIEWER'}
        response = self.client.post(self.list_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ==========================================================
    # 3. INACTIVE USER REJECTION
    # ==========================================================
    def test_inactive_user_cannot_be_added(self):
        self.client.force_authenticate(user=self.admin)
        payload = {'user_id': str(self.inactive_user.id), 'role': 'DEVELOPER'}
        response = self.client.post(self.list_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ==========================================================
    # 4. LIST MEMBERS (GET)
    # ==========================================================
    @patch('projects.services.send_in_app_notification')
    @patch('projects.services.log_activity')
    def test_admin_can_list_members(self, mock_log, mock_notify):
        ProjectMember.objects.create(
            project=self.project, user=self.developer,
            role=ProjectMemberRole.DEVELOPER, invited_by=self.manager
        )
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json().get('data', response.json())
        results = data.get('results', data) if isinstance(data, dict) else data
        self.assertGreaterEqual(len(results), 1)

    def test_developer_can_list_members_readonly(self):
        ProjectMember.objects.create(
            project=self.project, user=self.developer,
            role=ProjectMemberRole.DEVELOPER, invited_by=self.manager
        )
        self.client.force_authenticate(user=self.developer)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unauthenticated_cannot_list_members(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ==========================================================
    # 5. RETRIEVE MEMBER (GET /<pk>/)
    # ==========================================================
    def test_retrieve_member_detail(self):
        member = ProjectMember.objects.create(
            project=self.project, user=self.developer,
            role=ProjectMemberRole.DEVELOPER, invited_by=self.manager
        )
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.detail_url(member.pk))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json().get('data', response.json())
        self.assertEqual(data['role'], 'DEVELOPER')

    # ==========================================================
    # 6. UPDATE MEMBER ROLE (PATCH)
    # ==========================================================
    @patch('projects.services.send_in_app_notification')
    @patch('projects.services.log_activity')
    def test_admin_can_update_member_role(self, mock_log, mock_notify):
        member = ProjectMember.objects.create(
            project=self.project, user=self.developer,
            role=ProjectMemberRole.DEVELOPER, invited_by=self.manager
        )
        self.client.force_authenticate(user=self.admin)
        payload = {'role': 'MANAGER'}
        response = self.client.patch(self.detail_url(member.pk), payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        member.refresh_from_db()
        self.assertEqual(member.role, ProjectMemberRole.MANAGER)
        mock_log.assert_called_once()
        mock_notify.assert_called_once()

    @patch('projects.services.send_in_app_notification')
    @patch('projects.services.log_activity')
    def test_manager_can_update_member_role_in_own_project(self, mock_log, mock_notify):
        member = ProjectMember.objects.create(
            project=self.project, user=self.developer,
            role=ProjectMemberRole.DEVELOPER, invited_by=self.manager
        )
        self.client.force_authenticate(user=self.manager)
        payload = {'role': 'VIEWER'}
        response = self.client.patch(self.detail_url(member.pk), payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        member.refresh_from_db()
        self.assertEqual(member.role, ProjectMemberRole.VIEWER)

    def test_developer_cannot_update_member_role(self):
        member = ProjectMember.objects.create(
            project=self.project, user=self.developer2,
            role=ProjectMemberRole.DEVELOPER, invited_by=self.manager
        )
        self.client.force_authenticate(user=self.developer)
        payload = {'role': 'MANAGER'}
        response = self.client.patch(self.detail_url(member.pk), payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_invalid_role_rejected(self):
        member = ProjectMember.objects.create(
            project=self.project, user=self.developer,
            role=ProjectMemberRole.DEVELOPER, invited_by=self.manager
        )
        self.client.force_authenticate(user=self.admin)
        payload = {'role': 'SUPERADMIN'}
        response = self.client.patch(self.detail_url(member.pk), payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_without_role_rejected(self):
        member = ProjectMember.objects.create(
            project=self.project, user=self.developer,
            role=ProjectMemberRole.DEVELOPER, invited_by=self.manager
        )
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(self.detail_url(member.pk), {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ==========================================================
    # 7. REMOVE MEMBER (DELETE)
    # ==========================================================
    @patch('projects.services.send_in_app_notification')
    @patch('projects.services.log_activity')
    def test_admin_can_remove_member(self, mock_log, mock_notify):
        member = ProjectMember.objects.create(
            project=self.project, user=self.developer,
            role=ProjectMemberRole.DEVELOPER, invited_by=self.manager
        )
        member_pk = member.pk
        self.client.force_authenticate(user=self.admin)
        response = self.client.delete(self.detail_url(member_pk))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ProjectMember.objects.filter(pk=member_pk).exists())
        mock_log.assert_called_once()
        mock_notify.assert_called_once()

    @patch('projects.services.send_in_app_notification')
    @patch('projects.services.log_activity')
    def test_manager_can_remove_member_from_own_project(self, mock_log, mock_notify):
        member = ProjectMember.objects.create(
            project=self.project, user=self.developer2,
            role=ProjectMemberRole.DEVELOPER, invited_by=self.manager
        )
        member_pk = member.pk
        self.client.force_authenticate(user=self.manager)
        response = self.client.delete(self.detail_url(member_pk))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ProjectMember.objects.filter(pk=member_pk).exists())

    def test_developer_cannot_remove_member(self):
        member = ProjectMember.objects.create(
            project=self.project, user=self.developer2,
            role=ProjectMemberRole.DEVELOPER, invited_by=self.manager
        )
        self.client.force_authenticate(user=self.developer)
        response = self.client.delete(self.detail_url(member.pk))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_client_cannot_remove_member(self):
        member = ProjectMember.objects.create(
            project=self.project, user=self.developer2,
            role=ProjectMemberRole.DEVELOPER, invited_by=self.manager
        )
        self.client.force_authenticate(user=self.client_user)
        response = self.client.delete(self.detail_url(member.pk))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ==========================================================
    # 8. M2M SYNC VERIFICATION
    # ==========================================================
    @patch('projects.services.send_in_app_notification')
    @patch('projects.services.log_activity')
    def test_adding_developer_syncs_team_members(self, mock_log, mock_notify):
        self.client.force_authenticate(user=self.admin)
        payload = {'user_id': str(self.developer2.id), 'role': 'DEVELOPER'}
        self.client.post(self.list_url, payload)
        self.project.refresh_from_db()
        self.assertIn(
            self.developer2,
            self.project.team_members.all()
        )

    @patch('projects.services.send_in_app_notification')
    @patch('projects.services.log_activity')
    def test_removing_member_cleans_team_members(self, mock_log, mock_notify):
        member = ProjectMember.objects.create(
            project=self.project, user=self.developer2,
            role=ProjectMemberRole.DEVELOPER, invited_by=self.manager
        )
        self.project.team_members.add(self.developer2)
        self.client.force_authenticate(user=self.admin)
        self.client.delete(self.detail_url(member.pk))
        self.project.refresh_from_db()
        self.assertNotIn(
            self.developer2,
            self.project.team_members.all()
        )

    @patch('projects.services.send_in_app_notification')
    @patch('projects.services.log_activity')
    def test_role_update_syncs_team_members(self, mock_log, mock_notify):
        """Promoting a DEVELOPER to MANAGER should remove them from team_members M2M."""
        member = ProjectMember.objects.create(
            project=self.project, user=self.developer2,
            role=ProjectMemberRole.DEVELOPER, invited_by=self.manager
        )
        self.project.team_members.add(self.developer2)
        self.client.force_authenticate(user=self.admin)
        self.client.patch(self.detail_url(member.pk), {'role': 'MANAGER'})
        self.project.refresh_from_db()
        self.assertNotIn(
            self.developer2,
            self.project.team_members.all()
        )

    # ==========================================================
    # 9. NONEXISTENT USER HANDLING
    # ==========================================================
    def test_adding_nonexistent_user_returns_400(self):
        self.client.force_authenticate(user=self.admin)
        import uuid
        payload = {'user_id': str(uuid.uuid4()), 'role': 'DEVELOPER'}
        response = self.client.post(self.list_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
