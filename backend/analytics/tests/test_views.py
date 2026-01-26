from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from common.constants import ActionType, TargetType
from common.models import ActivityLog
from projects.constants import ProjectMemberRole, ProjectPriority, ProjectStatus
from projects.models import Project, ProjectMember
from tasks.constants import TaskPriority, TaskStatus
from tasks.models import Task

User = get_user_model()


class AnalyticsViewsTests(APITestCase):
    def setUp(self):
        self.manager = User.objects.create_user(
            email='manager@orbitpm.com',
            password='password123',
            full_name='Agency Manager',
            role=User.Roles.MANAGER,
        )
        self.other_manager = User.objects.create_user(
            email='other-manager@orbitpm.com',
            password='password123',
            full_name='Other Manager',
            role=User.Roles.MANAGER,
        )
        self.developer = User.objects.create_user(
            email='dev@orbitpm.com',
            password='password123',
            full_name='Orbit Developer',
            role=User.Roles.DEVELOPER,
        )
        self.client_user = User.objects.create_user(
            email='client@orbitpm.com',
            password='password123',
            full_name='Client User',
            role=User.Roles.CLIENT,
        )

        self.project = Project.objects.create(
            title='Analytics Portal',
            status=ProjectStatus.IN_PROGRESS,
            priority=ProjectPriority.HIGH,
            manager=self.manager,
            client=self.client_user,
            created_by=self.manager,
        )
        self.project.team_members.add(self.developer)
        ProjectMember.objects.create(
            project=self.project,
            user=self.developer,
            role=ProjectMemberRole.DEVELOPER,
            invited_by=self.manager,
        )

        self.other_project = Project.objects.create(
            title='Hidden Client Portal',
            status=ProjectStatus.PLANNING,
            priority=ProjectPriority.MEDIUM,
            manager=self.other_manager,
            created_by=self.other_manager,
        )

        self.completed_task = Task.objects.create(
            title='Ship dashboard cards',
            project=self.project,
            status=TaskStatus.COMPLETED,
            priority=TaskPriority.HIGH,
            assigned_to=self.developer,
            due_date=timezone.localdate(),
        )
        self.overdue_task = Task.objects.create(
            title='Reconcile workflow report',
            project=self.project,
            status=TaskStatus.TODO,
            priority=TaskPriority.URGENT,
            assigned_to=self.developer,
            due_date=timezone.localdate() - timedelta(days=1),
        )
        self.archived_task = Task.objects.create(
            title='Archive legacy milestone',
            project=self.project,
            status=TaskStatus.COMPLETED,
            priority=TaskPriority.LOW,
            assigned_to=self.manager,
            is_archived=True,
            due_date=timezone.localdate() - timedelta(days=2),
        )
        self.old_task = Task.objects.create(
            title='Old reporting cleanup',
            project=self.project,
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            assigned_to=self.developer,
            due_date=timezone.localdate() + timedelta(days=4),
        )
        Task.objects.filter(id=self.old_task.id).update(
            created_at=timezone.now() - timedelta(days=45),
        )

        Task.objects.create(
            title='Hidden project task',
            project=self.other_project,
            status=TaskStatus.COMPLETED,
            priority=TaskPriority.MEDIUM,
            assigned_to=self.other_manager,
            due_date=timezone.localdate(),
        )

        ActivityLog.objects.create(
            actor=self.manager,
            action_type=ActionType.CREATED,
            target_type=TargetType.PROJECT,
            target_id=str(self.project.id),
            target_repr=self.project.title,
            description='Project created.',
        )
        ActivityLog.objects.create(
            actor=self.developer,
            action_type=ActionType.STATUS_CHANGED,
            target_type=TargetType.TASK,
            target_id=str(self.completed_task.id),
            target_repr=self.completed_task.title,
            description='Task completed.',
        )

        self.dashboard_url = reverse('analytics_dashboard')
        self.project_summary_url = reverse(
            'analytics_project_summary',
            kwargs={'slug': self.project.slug},
        )

    def test_dashboard_metrics_are_scoped_and_chart_ready(self):
        self.client.force_authenticate(user=self.manager)

        response = self.client.get(self.dashboard_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data['data']
        self.assertEqual(data['total_projects'], 1)
        self.assertEqual(data['active_projects'], 1)
        self.assertEqual(data['total_tasks'], 4)
        self.assertEqual(data['completed_tasks'], 2)
        self.assertEqual(data['overdue_tasks'], 1)
        self.assertEqual(data['archived_tasks'], 1)
        self.assertEqual(data['task_completion_percentage'], 50.0)
        self.assertEqual(data['total_project_members'], 1)
        self.assertEqual(data['recent_activity_count'], 2)

        status_counts = {
            item['value']: item['count']
            for item in data['tasks_by_status']
        }
        priority_counts = {
            item['value']: item['count']
            for item in data['tasks_by_priority']
        }
        self.assertEqual(status_counts[TaskStatus.COMPLETED], 2)
        self.assertEqual(status_counts[TaskStatus.TODO], 2)
        self.assertEqual(priority_counts[TaskPriority.URGENT], 1)

        assignee_rows = {
            item['email']: item
            for item in data['assignment_workload']
        }
        self.assertEqual(assignee_rows[self.developer.email]['total_tasks'], 3)
        self.assertEqual(assignee_rows[self.developer.email]['overdue_tasks'], 1)

    def test_dashboard_supports_last_7_days_filter(self):
        self.client.force_authenticate(user=self.manager)

        response = self.client.get(self.dashboard_url, {'period': 'last_7_days'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data['data']
        self.assertEqual(data['date_range']['period'], 'last_7_days')
        self.assertEqual(data['total_tasks'], 3)
        self.assertEqual(data['completed_tasks'], 2)
        self.assertEqual(data['overdue_tasks'], 1)

    def test_project_summary_uses_accessible_tasks_for_user(self):
        self.client.force_authenticate(user=self.developer)

        response = self.client.get(self.project_summary_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data['data']
        self.assertEqual(data['project']['slug'], self.project.slug)
        self.assertEqual(data['total_tasks'], 3)
        self.assertEqual(data['completed_tasks'], 1)
        self.assertEqual(data['overdue_tasks'], 1)
        self.assertEqual(data['archived_tasks'], 0)
        self.assertEqual(data['active_members'], 1)

    def test_project_summary_hides_unauthorized_projects(self):
        self.client.force_authenticate(user=self.other_manager)

        response = self.client.get(self.project_summary_url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_custom_date_range_requires_bounds(self):
        self.client.force_authenticate(user=self.manager)

        response = self.client.get(self.dashboard_url, {'period': 'custom'})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('date_range', response.data['errors'])
