from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from projects.models import Project
from projects.constants import ProjectStatus, ProjectPriority
from tasks.models import Task
from tasks.constants import TaskStatus, TaskPriority

User = get_user_model()

class TaskAPITests(APITestCase):
    """
    Rigorously test Task REST API filtering, searching, and ordering functionality.
    """
    def setUp(self):
        # Create users
        self.admin = User.objects.create_user(
            email='admin@orbitpm.com', password='password123', full_name='Admin Boss', role=User.Roles.ADMIN
        )
        self.manager = User.objects.create_user(
            email='manager@orbitpm.com', password='password123', full_name='Manager Jack', role=User.Roles.MANAGER
        )
        self.developer = User.objects.create_user(
            email='dev@orbitpm.com', password='password123', full_name='Dev Jill', role=User.Roles.DEVELOPER
        )

        # Create Project
        self.project = Project.objects.create(
            title='Apollo Project Workspace',
            status=ProjectStatus.IN_PROGRESS,
            priority=ProjectPriority.HIGH,
            manager=self.manager,
            created_by=self.manager
        )
        self.project.team_members.add(self.developer)

        # Create Tasks with varied data for filtering, search, and ordering
        self.task1 = Task.objects.create(
            title='Build Frontend Routing',
            description='Setup SPA router and view structure.',
            project=self.project,
            status=TaskStatus.TODO,
            priority=TaskPriority.HIGH,
            assigned_to=self.developer,
            due_date=timezone.localdate() + timedelta(days=2)
        )
        
        self.task2 = Task.objects.create(
            title='Deploy Server Infrastructure',
            description='Configure staging server environment.',
            project=self.project,
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.MEDIUM,
            assigned_to=None,
            due_date=timezone.localdate() + timedelta(days=5)
        )
        
        self.task3 = Task.objects.create(
            title='Database Query Optimization',
            description='Optimize heavy postgres queries.',
            project=self.project,
            status=TaskStatus.IN_REVIEW,
            priority=TaskPriority.LOW,
            assigned_to=self.developer,
            due_date=timezone.localdate() + timedelta(days=1)
        )

        self.list_url = reverse('task-list')

    def test_filter_by_status(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.list_url, {'status': TaskStatus.TODO})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['data']['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], str(self.task1.id))

    def test_filter_by_priority(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.list_url, {'priority': TaskPriority.LOW})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['data']['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], str(self.task3.id))

    def test_filter_by_assigned_to(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.list_url, {'assigned_to': self.developer.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['data']['results']
        # task1 and task3 are assigned to self.developer
        self.assertEqual(len(results), 2)

    def test_filter_by_due_date_range(self):
        self.client.force_authenticate(user=self.admin)
        # Filter for tasks due in less than 3 days: task3 (1 day) and task1 (2 days)
        limit_date = timezone.localdate() + timedelta(days=3)
        response = self.client.get(self.list_url, {'due_date_lte': limit_date.isoformat()})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['data']['results']
        self.assertEqual(len(results), 2)
        task_ids = [res['id'] for res in results]
        self.assertIn(str(self.task1.id), task_ids)
        self.assertIn(str(self.task3.id), task_ids)

    def test_search_by_title_and_description(self):
        self.client.force_authenticate(user=self.admin)
        
        # Search title
        response = self.client.get(self.list_url, {'search': 'Frontend'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['data']['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], str(self.task1.id))

        # Search description
        response = self.client.get(self.list_url, {'search': 'postgres'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['data']['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], str(self.task3.id))

        # Search project title
        response = self.client.get(self.list_url, {'search': 'Apollo'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['data']['results']
        self.assertEqual(len(results), 3)

    def test_ordering(self):
        self.client.force_authenticate(user=self.admin)
        
        # Order by due_date ascending
        response = self.client.get(self.list_url, {'ordering': 'due_date'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['data']['results']
        # Order should be: task3 (1 day), task1 (2 days), task2 (5 days)
        self.assertEqual(results[0]['id'], str(self.task3.id))
        self.assertEqual(results[1]['id'], str(self.task1.id))
        self.assertEqual(results[2]['id'], str(self.task2.id))
