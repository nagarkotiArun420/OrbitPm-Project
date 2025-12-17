from django.test import TestCase
from django.contrib.auth import get_user_model
from projects.models import Project
from tasks.models import Task

User = get_user_model()

class TaskModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='dev@orbitpm.com',
            password='password123',
            full_name='Developer Staff',
            role=User.Roles.DEVELOPER
        )
        self.project = Project.objects.create(
            name='Alpha App',
            owner=self.user
        )

    def test_create_task_successful(self):
        task = Task.objects.create(
            title='Implement JWT',
            project=self.project,
            assigned_to=self.user,
            status=Task.TaskStatus.TODO,
            priority=Task.TaskPriority.HIGH
        )
        self.assertEqual(task.title, 'Implement JWT')
        self.assertEqual(task.project, self.project)
        self.assertEqual(task.assigned_to, self.user)
        self.assertEqual(task.priority, Task.TaskPriority.HIGH)
