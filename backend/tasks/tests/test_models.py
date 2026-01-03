from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from projects.models import Project
from projects.constants import ProjectStatus, ProjectPriority
from tasks.models import Task
from tasks.constants import TaskStatus, TaskPriority
from tasks.services import create_task, assign_task_to_user, transition_task_status

User = get_user_model()

class TaskArchitectureTests(TestCase):
    """
    Comprehensive test suite validating Task data architecture,
    relationships, automated slugs, due date bounds, team assignment guards,
    and workflow state transition validations.
    """
    def setUp(self):
        # Create users
        self.admin = User.objects.create_user(
            email='admin@orbitpm.com', password='password123', full_name='Admin Owner', role=User.Roles.ADMIN
        )
        self.manager = User.objects.create_user(
            email='manager@orbitpm.com', password='password123', full_name='Manager Jack', role=User.Roles.MANAGER
        )
        self.developer = User.objects.create_user(
            email='dev@orbitpm.com', password='password123', full_name='Developer Jill', role=User.Roles.DEVELOPER
        )
        self.non_team_user = User.objects.create_user(
            email='other@orbitpm.com', password='password123', full_name='Other Person', role=User.Roles.DEVELOPER
        )

        # Create Project
        self.project = Project.objects.create(
            title='Project X Portal',
            status=ProjectStatus.IN_PROGRESS,
            priority=ProjectPriority.HIGH,
            start_date=timezone.localdate() - timedelta(days=5),
            deadline=timezone.localdate() + timedelta(days=30),
            manager=self.manager,
            created_by=self.manager
        )
        self.project.team_members.add(self.developer)

    # ==========================================
    # 1. CORE CREATION & SLUGS
    # ==========================================
    def test_task_creation_and_auto_slug(self):
        task = Task.objects.create(
            title='Build Auth Middleware',
            description='Standard JWT authentication setup.',
            project=self.project,
            status=TaskStatus.TODO,
            priority=TaskPriority.HIGH,
            assigned_by=self.manager
        )
        self.assertEqual(task.slug, 'build-auth-middleware')
        self.assertEqual(str(task), f"{task.title} ({task.status})")
        self.assertEqual(task.status, TaskStatus.TODO)
        self.assertIsNone(task.completed_at)

    def test_task_slug_collision_resolves(self):
        task1 = Task.objects.create(title='Design System', project=self.project)
        task2 = Task.objects.create(title='Design System', project=self.project)
        self.assertEqual(task1.slug, 'design-system')
        self.assertEqual(task2.slug, 'design-system-1')

    # ==========================================
    # 2. NUMERIC HOUR VALIDATIONS
    # ==========================================
    def test_estimated_and_actual_hours_non_negative(self):
        task = Task(title='Negative Estimations', project=self.project, estimated_hours=Decimal('-5.00'))
        with self.assertRaises(ValidationError):
            task.full_clean()

        task2 = Task(title='Negative Actuals', project=self.project, actual_hours=Decimal('-1.50'))
        with self.assertRaises(ValidationError):
            task2.full_clean()

    # ==========================================
    # 3. TIMELINE & DUE DATE VALIDATIONS
    # ==========================================
    def test_due_date_aligns_with_project_timeline(self):
        # Before project start date
        invalid_due_early = Task(
            title='Early Due Task',
            project=self.project,
            due_date=self.project.start_date - timedelta(days=1)
        )
        with self.assertRaises(ValidationError):
            invalid_due_early.full_clean()

        # After project deadline
        invalid_due_late = Task(
            title='Late Due Task',
            project=self.project,
            due_date=self.project.deadline + timedelta(days=1)
        )
        with self.assertRaises(ValidationError):
            invalid_due_late.full_clean()

        # Valid due date
        valid_task = Task(
            title='Valid Due Task',
            project=self.project,
            due_date=self.project.start_date + timedelta(days=5)
        )
        valid_task.full_clean()  # Should not raise

    # ==========================================
    # 4. ASSIGNMENT & TEAM GUARDS
    # ==========================================
    def test_assigned_user_must_be_in_project_team(self):
        # Dev belongs to the team (added as team_member)
        valid_assignment = Task(
            title='Valid Dev Assigned',
            project=self.project,
            assigned_to=self.developer
        )
        valid_assignment.full_clean()  # Should not raise

        # Manager belongs to the team (project.manager)
        valid_mgr_assignment = Task(
            title='Valid Manager Assigned',
            project=self.project,
            assigned_to=self.manager
        )
        valid_mgr_assignment.full_clean()  # Should not raise

        # Non-team user does NOT belong to project team
        invalid_assignment = Task(
            title='Invalid User Assigned',
            project=self.project,
            assigned_to=self.non_team_user
        )
        with self.assertRaises(ValidationError):
            invalid_assignment.full_clean()

    # ==========================================
    # 5. AUTOMATED COMPLETION LIFECYCLE
    # ==========================================
    def test_completed_status_sets_timestamp(self):
        task = Task.objects.create(
            title='Perform API Refactoring',
            project=self.project,
            status=TaskStatus.TODO
        )
        self.assertIsNone(task.completed_at)

        # Transition to completed
        task.status = TaskStatus.COMPLETED
        task.save()
        self.assertIsNotNone(task.completed_at)

        # Reopen task (transition back to todo)
        task.status = TaskStatus.TODO
        task.save()
        self.assertIsNone(task.completed_at)

    # ==========================================
    # 6. TRANSACTIONAL SERVICE AND STATE MACHINE
    # ==========================================
    def test_create_task_service(self):
        task = create_task(
            project=self.project,
            title='Draft Technical Spec',
            created_by=self.manager,
            estimated_hours=Decimal('8.00')
        )
        self.assertEqual(task.title, 'Draft Technical Spec')
        self.assertEqual(task.assigned_by, self.manager)

    def test_assign_task_service(self):
        task = Task.objects.create(title='Code Review Tasks', project=self.project)
        assign_task_to_user(task, self.developer, assigned_by=self.manager)
        self.assertEqual(task.assigned_to, self.developer)
        self.assertEqual(task.assigned_by, self.manager)

    def test_workflow_transitions(self):
        from tasks.validators import get_valid_next_statuses
        
        task = Task.objects.create(
            title='Setup CI Pipeline',
            project=self.project,
            status=TaskStatus.TODO
        )

        # 1. Verify get_valid_next_statuses output
        self.assertEqual(get_valid_next_statuses(TaskStatus.TODO), [TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED])
        self.assertEqual(get_valid_next_statuses(TaskStatus.COMPLETED), [])

        # 2. Valid transition: TODO -> IN_PROGRESS
        transition_task_status(task, TaskStatus.IN_PROGRESS)
        self.assertEqual(task.status, TaskStatus.IN_PROGRESS)

        # 3. Invalid transition: IN_PROGRESS -> TODO (no longer allowed under strict rules)
        with self.assertRaises(ValidationError):
            transition_task_status(task, TaskStatus.TODO)

        # 4. Invalid transition: IN_PROGRESS -> COMPLETED (requires review)
        with self.assertRaises(ValidationError):
            transition_task_status(task, TaskStatus.COMPLETED)

        # 5. Valid transition: IN_PROGRESS -> IN_REVIEW
        transition_task_status(task, TaskStatus.IN_REVIEW)
        self.assertEqual(task.status, TaskStatus.IN_REVIEW)

        # 6. Valid transition: IN_REVIEW -> COMPLETED
        transition_task_status(task, TaskStatus.COMPLETED)
        self.assertEqual(task.status, TaskStatus.COMPLETED)
        self.assertIsNotNone(task.completed_at)

        # 7. Invalid transition: COMPLETED -> TODO (cannot transition further from completed)
        with self.assertRaises(ValidationError):
            transition_task_status(task, TaskStatus.TODO)

    def test_task_assignment_rules(self):
        from tasks.validators import validate_task_assignment
        
        # 1. Clients cannot be assigned tasks
        client_user = User.objects.create_user(
            email='client@orbitpm.com', password='password123', full_name='Client User', role=User.Roles.CLIENT
        )
        self.project.team_members.add(client_user) # Try adding client to project team
        
        task = Task.objects.create(title='Some Task', project=self.project)
        with self.assertRaises(ValidationError):
            validate_task_assignment(task, client_user, actor=self.admin)
            
        # 2. Inactive users cannot receive assignments
        inactive_user = User.objects.create_user(
            email='inactive@orbitpm.com', password='password123', full_name='Inactive Dev', role=User.Roles.DEVELOPER, is_active=False
        )
        self.project.team_members.add(inactive_user)
        with self.assertRaises(ValidationError):
            validate_task_assignment(task, inactive_user, actor=self.admin)
            
        # 3. Completed tasks cannot be reassigned
        completed_task = Task.objects.create(
            title='Completed Task',
            project=self.project,
            status=TaskStatus.COMPLETED
        )
        with self.assertRaises(ValidationError):
            validate_task_assignment(completed_task, self.developer, actor=self.admin)
            
        # 4. Role-based assignment: Admin can assign any task
        validate_task_assignment(task, self.developer, actor=self.admin) # Should pass
        
        # 5. Manager can assign tasks in managed project
        validate_task_assignment(task, self.developer, actor=self.manager) # Should pass
        
        # Manager cannot assign tasks in projects they do NOT manage
        other_manager = User.objects.create_user(
            email='other_mgr@orbitpm.com', password='password123', role=User.Roles.MANAGER
        )
        with self.assertRaises(ValidationError):
            validate_task_assignment(task, self.developer, actor=other_manager)
            
        # 6. Developer cannot assign tasks to others
        other_developer = User.objects.create_user(
            email='other_dev@orbitpm.com', password='password123', role=User.Roles.DEVELOPER
        )
        self.project.team_members.add(other_developer)
        with self.assertRaises(ValidationError):
            validate_task_assignment(task, other_developer, actor=self.developer)
            
        # Developer can assign tasks to themselves
        validate_task_assignment(task, self.developer, actor=self.developer) # Should pass
        
        # Developer can unassign themselves (set assignee to None)
        task.assigned_to = self.developer
        validate_task_assignment(task, None, actor=self.developer) # Should pass
        
        # 7. Client cannot assign tasks
        with self.assertRaises(ValidationError):
            validate_task_assignment(task, self.developer, actor=client_user)
