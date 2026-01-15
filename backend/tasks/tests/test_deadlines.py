from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from common.models import ActivityLog
from notifications.models import Notification
from projects.constants import ProjectPriority, ProjectStatus
from projects.models import Project
from tasks.constants import TaskPriority, TaskStatus
from tasks.models import Task
from tasks.services import (
    detect_overdue_tasks,
    generate_overdue_task_notifications,
    generate_upcoming_deadline_notifications,
    get_upcoming_deadlines,
)

User = get_user_model()


class TaskDeadlineLogicTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user(
            email='manager.deadlines@orbitpm.com',
            password='password123',
            full_name='Deadline Manager',
            role=User.Roles.MANAGER,
        )
        self.developer = User.objects.create_user(
            email='developer.deadlines@orbitpm.com',
            password='password123',
            full_name='Deadline Developer',
            role=User.Roles.DEVELOPER,
        )
        self.project = Project.objects.create(
            title='Deadline Monitoring Project',
            status=ProjectStatus.IN_PROGRESS,
            priority=ProjectPriority.HIGH,
            start_date=timezone.localdate() - timedelta(days=30),
            deadline=timezone.localdate() + timedelta(days=30),
            manager=self.manager,
            created_by=self.manager,
        )
        self.project.team_members.add(self.developer)

    def create_task(self, title, due_delta, **kwargs):
        return Task.objects.create(
            title=title,
            project=self.project,
            assigned_to=kwargs.pop('assigned_to', self.developer),
            priority=TaskPriority.MEDIUM,
            due_date=timezone.localdate() + timedelta(days=due_delta),
            **kwargs
        )

    def test_overdue_properties_and_querysets_exclude_terminal_states(self):
        overdue = self.create_task('Overdue task', -2)
        completed = self.create_task(
            'Completed overdue task',
            -2,
            status=TaskStatus.COMPLETED,
        )
        archived = self.create_task(
            'Archived overdue task',
            -2,
            status=TaskStatus.COMPLETED,
            is_archived=True,
        )
        deleted = self.create_task('Deleted overdue task', -2)
        deleted.is_deleted = True
        deleted.deleted_at = timezone.now()
        deleted.deleted_by = self.manager
        deleted.save()

        self.assertTrue(overdue.is_overdue)
        self.assertEqual(overdue.overdue_duration.days, 2)
        self.assertFalse(completed.is_overdue)
        self.assertFalse(archived.is_overdue)
        self.assertFalse(deleted.is_overdue)
        self.assertEqual(list(Task.objects.overdue()), [overdue])
        self.assertIn(completed, Task.objects.completed())

    def test_deadline_service_queries_and_notifications_are_idempotent(self):
        overdue = self.create_task('Notify overdue task', -1)
        today = self.create_task('Notify today task', 0)
        upcoming = self.create_task('Notify upcoming task', 2)
        self.create_task('Outside warning window task', 8)

        self.assertEqual(list(detect_overdue_tasks()), [overdue])
        self.assertEqual(set(get_upcoming_deadlines(days=3)), {today, upcoming})

        overdue_notifications = generate_overdue_task_notifications()
        upcoming_notifications = generate_upcoming_deadline_notifications(days=3)

        self.assertEqual(len(overdue_notifications), 2)
        self.assertEqual(len(upcoming_notifications), 4)
        self.assertEqual(Notification.objects.count(), 6)
        self.assertEqual(
            ActivityLog.objects.filter(
                target_id=str(overdue.id),
                metadata__deadline_event='overdue_detected',
            ).count(),
            1,
        )

        generate_overdue_task_notifications()
        generate_upcoming_deadline_notifications(days=3)
        self.assertEqual(Notification.objects.count(), 6)


class TaskDeadlineAPIFilterTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email='admin.deadlines@orbitpm.com',
            password='password123',
            full_name='Deadline Admin',
            role=User.Roles.ADMIN,
        )
        self.manager = User.objects.create_user(
            email='manager.api.deadlines@orbitpm.com',
            password='password123',
            full_name='API Deadline Manager',
            role=User.Roles.MANAGER,
        )
        self.developer = User.objects.create_user(
            email='developer.api.deadlines@orbitpm.com',
            password='password123',
            full_name='API Deadline Developer',
            role=User.Roles.DEVELOPER,
        )
        self.project = Project.objects.create(
            title='Deadline API Project',
            status=ProjectStatus.IN_PROGRESS,
            priority=ProjectPriority.HIGH,
            start_date=timezone.localdate() - timedelta(days=30),
            deadline=timezone.localdate() + timedelta(days=30),
            manager=self.manager,
            created_by=self.manager,
        )
        self.project.team_members.add(self.developer)
        self.overdue = self.create_task('API overdue task', -1)
        self.due_today = self.create_task('API due today task', 0)
        self.upcoming = self.create_task('API upcoming task', 2)
        self.future = self.create_task('API future task', 8)
        self.list_url = reverse('task-list')

    def create_task(self, title, due_delta):
        return Task.objects.create(
            title=title,
            project=self.project,
            assigned_to=self.developer,
            due_date=timezone.localdate() + timedelta(days=due_delta),
        )

    def get_result_ids(self, response):
        return {item['id'] for item in response.data['data']['results']}

    def test_deadline_filters(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(self.list_url, {'overdue': 'true'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.get_result_ids(response), {str(self.overdue.id)})
        self.assertTrue(response.data['data']['results'][0]['is_overdue'])

        response = self.client.get(self.list_url, {'due_today': 'true'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.get_result_ids(response), {str(self.due_today.id)})

        response = self.client.get(self.list_url, {'upcoming_deadlines': 'true'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.get_result_ids(response), {str(self.upcoming.id)})

        response = self.client.get(self.list_url, {'upcoming_days': '1'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.get_result_ids(response), set())
