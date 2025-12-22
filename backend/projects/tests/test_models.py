from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from projects.models import Project
from projects.constants import ProjectStatus, ProjectPriority

User = get_user_model()

class ProjectModelTests(TestCase):
    """
    Rigorously test Project database schemas, validations, slugs, and lifecycles.
    """
    def setUp(self):
        self.manager = User.objects.create_user(
            email='manager@orbitpm.com',
            password='password123',
            full_name='Agency Manager',
            role=User.Roles.MANAGER
        )
        self.client = User.objects.create_user(
            email='client@orbitpm.com',
            password='password123',
            full_name='Client Admin',
            role=User.Roles.CLIENT
        )

    def test_create_project_successful_with_defaults(self):
        """
        Verify successful project scaffold with default values.
        """
        project = Project.objects.create(
            title='Alpha Portal Redesign',
            description='Client portal design matching new guidelines.',
            manager=self.manager,
            client=self.client,
            created_by=self.manager
        )
        self.assertEqual(project.title, 'Alpha Portal Redesign')
        self.assertEqual(project.status, ProjectStatus.PLANNING)
        self.assertEqual(project.priority, ProjectPriority.MEDIUM)
        self.assertEqual(project.slug, 'alpha-portal-redesign')
        self.assertIsNone(project.start_date)
        self.assertIsNone(project.deadline)
        self.assertIsNone(project.completed_at)
        self.assertIsNone(project.budget)

    def test_slug_uniqueness_resolution(self):
        """
        Verify that duplicate titles resolve to distinct, unique slugs.
        """
        project1 = Project.objects.create(
            title='Acme Portal',
            manager=self.manager
        )
        project2 = Project.objects.create(
            title='Acme Portal',
            manager=self.manager
        )
        project3 = Project.objects.create(
            title='Acme Portal',
            manager=self.manager
        )
        
        self.assertEqual(project1.slug, 'acme-portal')
        self.assertEqual(project2.slug, 'acme-portal-1')
        self.assertEqual(project3.slug, 'acme-portal-2')

    def test_deadline_cannot_be_before_start_date(self):
        """
        Verify that having a deadline before start_date throws a ValidationError.
        """
        today = timezone.localdate()
        yesterday = today - timedelta(days=1)
        
        project = Project(
            title='Invalid Timeline Project',
            start_date=today,
            deadline=yesterday,
            manager=self.manager
        )
        
        with self.assertRaises(ValidationError) as ctx:
            project.save()
        
        # Check that 'deadline' is specifically flagged in the error message
        self.assertIn('deadline', ctx.exception.message_dict)
        self.assertEqual(
            ctx.exception.message_dict['deadline'][0],
            'The project deadline cannot be before the start date.'
        )

    def test_budget_cannot_be_negative(self):
        """
        Verify that negative budget values are caught by our validate_budget_positive rule.
        """
        project = Project(
            title='Negative Budget Project',
            budget=Decimal('-150.00'),
            manager=self.manager
        )
        
        with self.assertRaises(ValidationError) as ctx:
            project.save()
            
        self.assertIn('budget', ctx.exception.message_dict)

    def test_completed_at_lifecycle_rules(self):
        """
        Verify that changing status to COMPLETED triggers automated completed_at setting,
        and shifting it back resets it.
        """
        project = Project.objects.create(
            title='Milestone Release',
            manager=self.manager,
            status=ProjectStatus.IN_PROGRESS
        )
        self.assertIsNone(project.completed_at)
        
        # Shifting to COMPLETED
        project.status = ProjectStatus.COMPLETED
        project.save()
        
        self.assertIsNotNone(project.completed_at)
        # Ensure it is close to current time
        self.assertLessEqual(timezone.now() - project.completed_at, timedelta(seconds=5))
        
        # Shifting away from COMPLETED
        project.status = ProjectStatus.ON_HOLD
        project.save()
        self.assertIsNone(project.completed_at)

    def test_meta_ordering_newest_first(self):
        """
        Verify meta ordering pulls projects newest-created first.
        """
        p1 = Project.objects.create(title='First Project', manager=self.manager)
        p2 = Project.objects.create(title='Second Project', manager=self.manager)
        
        projects = list(Project.objects.all())
        self.assertEqual(projects[0], p2)
        self.assertEqual(projects[1], p1)
