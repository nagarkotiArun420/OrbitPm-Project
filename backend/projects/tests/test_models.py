from django.test import TestCase
from django.contrib.auth import get_user_model
from projects.models import Project

User = get_user_model()

class ProjectModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='manager@orbitpm.com',
            password='password123',
            full_name='Agency Manager',
            role=User.Roles.MANAGER
        )

    def test_create_project_successful(self):
        project = Project.objects.create(
            name='Alpha Website',
            description='Client website overhaul',
            status=Project.ProjectStatus.ACTIVE,
            owner=self.user
        )
        self.assertEqual(project.name, 'Alpha Website')
        self.assertEqual(project.owner, self.user)
        self.assertEqual(project.status, Project.ProjectStatus.ACTIVE)
