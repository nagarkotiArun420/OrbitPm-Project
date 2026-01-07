import datetime
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from common.models import ActivityLog
from common.constants import ActionType, TargetType
from common.services import log_activity
from projects.models import Project
from projects.services import create_project, update_project, delete_project
from tasks.models import Task
from tasks.services import (
    create_task,
    update_task,
    delete_task,
    assign_task_to_user,
    transition_task_status,
)
from tasks.constants import TaskStatus

User = get_user_model()

class ActivityLogTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.request_factory = RequestFactory()
        
        # Create users
        self.manager = User.objects.create_user(
            email='manager@orbitpm.com',
            password='password123',
            full_name='Agency Manager',
            role=User.Roles.MANAGER
        )
        self.developer = User.objects.create_user(
            email='developer@orbitpm.com',
            password='password123',
            full_name='Lead Developer',
            role=User.Roles.DEVELOPER
        )

        # Authenticate client as manager by default
        self.client.force_authenticate(user=self.manager)

    def test_log_activity_with_request_context(self):
        """
        Verify log_activity extracts user actor and IP address correctly from request.
        """
        request = self.request_factory.get('/api/v1/dummy/', REMOTE_ADDR='198.51.100.42')
        request.user = self.manager
        
        log = log_activity(
            action_type=ActionType.UPDATED,
            target_type=TargetType.PROJECT,
            target_id='some-uuid',
            target_repr='Test Log',
            description='Test request log',
            request=request
        )
        
        self.assertIsNotNone(log)
        self.assertEqual(log.actor, self.manager)
        self.assertEqual(log.ip_address, '198.51.100.42')
        self.assertEqual(log.action_type, ActionType.UPDATED)

    def test_project_creation_logging(self):
        """
        Verify create_project triggers a CREATED log.
        """
        project = create_project(
            created_by=self.manager,
            title='Web Orbit App',
            description='Orbit app implementation'
        )
        
        logs = ActivityLog.objects.filter(target_type=TargetType.PROJECT, target_id=project.id)
        self.assertEqual(logs.count(), 1)
        log = logs.first()
        self.assertEqual(log.action_type, ActionType.CREATED)
        self.assertEqual(log.actor, self.manager)
        self.assertIn('Web Orbit App', log.target_repr)

    def test_project_update_logging(self):
        """
        Verify update_project triggers an UPDATED log with metadata changes.
        """
        project = create_project(
            created_by=self.manager,
            title='Initial Title',
            description='Initial Description'
        )
        
        # Clear logs from creation
        ActivityLog.objects.all().delete()
        
        update_project(
            project=project,
            title='New Title',
            description='New Description'
        )
        
        logs = ActivityLog.objects.filter(target_type=TargetType.PROJECT, target_id=project.id)
        self.assertEqual(logs.count(), 1)
        log = logs.first()
        self.assertEqual(log.action_type, ActionType.UPDATED)
        self.assertIn('changes', log.metadata)
        self.assertEqual(log.metadata['changes']['title']['old'], 'Initial Title')
        self.assertEqual(log.metadata['changes']['title']['new'], 'New Title')

    def test_project_deletion_logging(self):
        """
        Verify delete_project triggers a DELETED log before record is deleted.
        """
        project = create_project(
            created_by=self.manager,
            title='Ghost Project'
        )
        
        project_id = project.id
        delete_project(project=project)
        
        logs = ActivityLog.objects.filter(target_type=TargetType.PROJECT, target_id=project_id)
        self.assertEqual(logs.count(), 2)  # 1 for creation, 1 for deletion
        deletion_log = logs.filter(action_type=ActionType.DELETED).first()
        self.assertIsNotNone(deletion_log)
        self.assertEqual(deletion_log.target_repr, 'Ghost Project')

    def test_task_creation_logging(self):
        """
        Verify create_task triggers a CREATED log.
        """
        project = create_project(
            created_by=self.manager,
            title='Parent Project'
        )
        
        task = create_task(
            project=project,
            title='Implement Logging Engine',
            created_by=self.manager
        )
        
        logs = ActivityLog.objects.filter(target_type=TargetType.TASK, target_id=task.id)
        self.assertEqual(logs.count(), 1)
        log = logs.first()
        self.assertEqual(log.action_type, ActionType.CREATED)
        self.assertEqual(log.actor, self.manager)

    def test_task_assignment_logging(self):
        """
        Verify assigning task triggers an ASSIGNED log with email metadata.
        """
        project = create_project(
            created_by=self.manager,
            title='Parent Project'
        )
        # Associate developer to team
        project.team_members.add(self.developer)
        
        task = create_task(
            project=project,
            title='Assign Me',
            created_by=self.manager
        )
        
        assign_task_to_user(task=task, user=self.developer, assigned_by=self.manager)
        
        logs = ActivityLog.objects.filter(target_type=TargetType.TASK, target_id=task.id, action_type=ActionType.ASSIGNED)
        self.assertEqual(logs.count(), 1)
        log = logs.first()
        self.assertEqual(log.metadata['old_assignee_email'], None)
        self.assertEqual(log.metadata['new_assignee_email'], self.developer.email)

    def test_task_status_transition_logging(self):
        """
        Verify status transition triggers STATUS_CHANGED log.
        """
        project = create_project(
            created_by=self.manager,
            title='Parent Project'
        )
        task = create_task(
            project=project,
            title='Status Transition Task',
            created_by=self.manager
        )
        
        transition_task_status(task=task, new_status=TaskStatus.IN_PROGRESS)
        
        logs = ActivityLog.objects.filter(target_type=TargetType.TASK, target_id=task.id, action_type=ActionType.STATUS_CHANGED)
        self.assertEqual(logs.count(), 1)
        log = logs.first()
        self.assertEqual(log.metadata['old_status'], TaskStatus.TODO)
        self.assertEqual(log.metadata['new_status'], TaskStatus.IN_PROGRESS)

    def test_login_logout_logging(self):
        """
        Verify hitting login API triggers a LOGIN log and logout API triggers a LOGOUT log.
        """
        # Test Login log
        url_login = reverse('auth_login')
        response = self.client.post(url_login, {
            'email': 'manager@orbitpm.com',
            'password': 'password123'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify login log
        login_logs = ActivityLog.objects.filter(action_type=ActionType.LOGIN, actor=self.manager)
        self.assertEqual(login_logs.count(), 1)
        self.assertEqual(login_logs.first().target_repr, self.manager.email)
        
        # Extract refresh token
        refresh_token = response.data['refresh']
        
        # Log out
        url_logout = reverse('auth_logout')
        response_logout = self.client.post(url_logout, {
            'refresh': refresh_token
        })
        self.assertEqual(response_logout.status_code, status.HTTP_200_OK)
        
        # Verify logout log
        logout_logs = ActivityLog.objects.filter(action_type=ActionType.LOGOUT, actor=self.manager)
        self.assertEqual(logout_logs.count(), 1)
        self.assertEqual(logout_logs.first().target_repr, self.manager.email)
