from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError
from datetime import timedelta
from django.utils import timezone
from decimal import Decimal
from projects.models import Project
from projects.constants import ProjectStatus, ProjectPriority
from accounts.serializers import UserMinSerializer
from projects.serializers import (
    ProjectListSerializer,
    ProjectDetailSerializer,
    ProjectCreateSerializer,
    ProjectUpdateSerializer
)

User = get_user_model()

class ProjectSerializerTests(TestCase):
    """
    Rigorously test serializer schemas, data representations, and input boundary validations.
    """
    def setUp(self):
        # Create users representing all SaaS roles
        self.admin = User.objects.create_user(
            email='admin@orbitpm.com',
            password='password123',
            full_name='System Admin',
            role=User.Roles.ADMIN
        )
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
        self.client = User.objects.create_user(
            email='client@orbitpm.com',
            password='password123',
            full_name='Enterprise Client',
            role=User.Roles.CLIENT
        )

        # Baseline project instance
        self.project = Project.objects.create(
            title='Beta Portal Integration',
            description='Integrate third-party analytics API',
            status=ProjectStatus.IN_PROGRESS,
            priority=ProjectPriority.HIGH,
            start_date=timezone.localdate(),
            deadline=timezone.localdate() + timedelta(days=30),
            budget=Decimal('5000.00'),
            manager=self.manager,
            client=self.client,
            created_by=self.admin
        )
        self.project.team_members.add(self.developer)

    def test_user_min_serializer_omits_sensitive_fields(self):
        """
        Verify lightweight user serializer does not leak security parameters (password, credentials, superuser access).
        """
        serializer = UserMinSerializer(self.admin)
        data = serializer.data
        
        # Verify exposed fields
        self.assertEqual(data['id'], str(self.admin.id))
        self.assertEqual(data['email'], 'admin@orbitpm.com')
        self.assertEqual(data['full_name'], 'System Admin')
        self.assertEqual(data['role'], 'ADMIN')
        self.assertIn('avatar', data)
        
        # Verify omitted sensitive fields
        self.assertNotIn('password', data)
        self.assertNotIn('is_staff', data)
        self.assertNotIn('is_superuser', data)
        self.assertNotIn('user_permissions', data)
        self.assertNotIn('groups', data)

    def test_project_list_serializer_representation(self):
        """
        Verify that list serializer returns only listing attributes and nests manager correctly.
        """
        serializer = ProjectListSerializer(self.project)
        data = serializer.data
        
        expected_keys = {'id', 'title', 'slug', 'status', 'priority', 'deadline', 'manager', 'created_at'}
        self.assertEqual(set(data.keys()), expected_keys)
        
        # Manager should be properly nested and lightweight
        self.assertEqual(data['manager']['email'], 'manager@orbitpm.com')
        self.assertNotIn('is_staff', data['manager'])

    def test_project_detail_serializer_representation(self):
        """
        Verify detail serializer returns all parameters with expanded nested actors.
        """
        serializer = ProjectDetailSerializer(self.project)
        data = serializer.data
        
        self.assertEqual(data['title'], 'Beta Portal Integration')
        self.assertEqual(data['description'], 'Integrate third-party analytics API')
        self.assertEqual(data['budget'], '5000.00')
        
        # Nests
        self.assertEqual(data['manager']['full_name'], 'Agency Manager')
        self.assertEqual(data['client']['full_name'], 'Enterprise Client')
        self.assertEqual(data['created_by']['full_name'], 'System Admin')
        self.assertEqual(len(data['team_members']), 1)
        self.assertEqual(data['team_members'][0]['full_name'], 'Lead Developer')

    def test_project_create_serializer_validates_successfully(self):
        """
        Verify that valid input data validates with no errors.
        """
        payload = {
            'title': 'New Portal Project',
            'description': 'Description text',
            'status': ProjectStatus.PLANNING,
            'priority': ProjectPriority.LOW,
            'start_date': timezone.localdate(),
            'deadline': timezone.localdate() + timedelta(days=15),
            'budget': '12500.50',
            'client': self.client.id,
            'manager': self.manager.id,
            'team_members': [self.developer.id]
        }
        serializer = ProjectCreateSerializer(data=payload)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        
        instance = serializer.save()
        self.assertEqual(instance.title, 'New Portal Project')
        self.assertEqual(instance.slug, 'new-portal-project')
        self.assertEqual(instance.budget, Decimal('12500.50'))

    def test_project_create_serializer_duplicate_title_rejected(self):
        """
        Verify case-insensitive uniqueness checks trigger a title ValidationError.
        """
        # "beta portal integration" matches our setup project "Beta Portal Integration"
        payload = {
            'title': 'beta portal integration',
            'manager': self.manager.id
        }
        serializer = ProjectCreateSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn('title', serializer.errors)
        self.assertEqual(serializer.errors['title'][0], 'A project with this title already exists.')

    def test_project_create_serializer_negative_budget_rejected(self):
        """
        Verify budget bounds checks trigger a budget ValidationError.
        """
        payload = {
            'title': 'Unique Budget Project',
            'budget': '-2500.00',
            'manager': self.manager.id
        }
        serializer = ProjectCreateSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn('budget', serializer.errors)

    def test_project_create_serializer_invalid_manager_role_rejected(self):
        """
        Verify that assigning a non-manager/non-admin user as project manager fails.
        """
        # Assigning a user with role DEVELOPER as manager
        payload = {
            'title': 'Developer Managed Project',
            'manager': self.developer.id
        }
        serializer = ProjectCreateSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn('manager', serializer.errors)
        self.assertEqual(serializer.errors['manager'][0], 'The assigned manager must have the ADMIN or MANAGER role.')

    def test_project_create_serializer_invalid_client_role_rejected(self):
        """
        Verify that assigning a non-client user as project client fails.
        """
        # Assigning a user with role MANAGER as client
        payload = {
            'title': 'Manager Client Project',
            'client': self.manager.id,
            'manager': self.manager.id
        }
        serializer = ProjectCreateSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn('client', serializer.errors)
        self.assertEqual(serializer.errors['client'][0], 'The assigned client must have the CLIENT role.')

    def test_project_create_serializer_timeline_boundaries_rejected(self):
        """
        Verify that having deadline prior to start_date fails validation.
        """
        payload = {
            'title': 'Timeline Project',
            'start_date': timezone.localdate(),
            'deadline': timezone.localdate() - timedelta(days=2),
            'manager': self.manager.id
        }
        serializer = ProjectCreateSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn('deadline', serializer.errors)

    def test_project_update_serializer_patch_timeline_boundaries_rejected(self):
        """
        Verify that partial updates (PATCH) check deadline constraints against persisted instance values.
        """
        # Currently, self.project's start_date is today, and deadline is +30 days.
        # Let's perform a PATCH updating ONLY the deadline to be yesterday.
        payload = {
            'deadline': timezone.localdate() - timedelta(days=1)
        }
        serializer = ProjectUpdateSerializer(instance=self.project, data=payload, partial=True)
        self.assertFalse(serializer.is_valid())
        self.assertIn('deadline', serializer.errors)
