from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from projects.models import Project
from projects.constants import ProjectStatus, ProjectPriority
from tasks.models import Task, TaskComment
from tasks.constants import TaskStatus, TaskPriority
from common.models import ActivityLog

User = get_user_model()


class TaskCommentTests(APITestCase):

    def setUp(self):
        # ---------------- USERS ----------------
        self.admin = User.objects.create_user(
            email='admin@orbitpm.com',
            password='password123',
            full_name='Admin Boss',
            role=User.Roles.ADMIN
        )

        self.manager = User.objects.create_user(
            email='manager@orbitpm.com',
            password='password123',
            full_name='Manager Jack',
            role=User.Roles.MANAGER
        )

        self.developer = User.objects.create_user(
            email='dev@orbitpm.com',
            password='password123',
            full_name='Dev Jill',
            role=User.Roles.DEVELOPER
        )

        self.other_developer = User.objects.create_user(
            email='other_dev@orbitpm.com',
            password='password123',
            full_name='Dev Joe',
            role=User.Roles.DEVELOPER
        )

        self.client_user = User.objects.create_user(
            email='client@orbitpm.com',
            password='password123',
            full_name='Client Bob',
            role=User.Roles.CLIENT
        )

        # ---------------- PROJECT ----------------
        self.project = Project.objects.create(
            title='Apollo Project Workspace',
            status=ProjectStatus.IN_PROGRESS,
            priority=ProjectPriority.HIGH,
            manager=self.manager,
            created_by=self.manager
        )

        self.project.team_members.add(self.developer, self.other_developer)
        self.project.client = self.client_user
        self.project.save()

        # ---------------- TASKS ----------------
        self.task = Task.objects.create(
            project=self.project,
            title='Develop task comments backend',
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.HIGH,
            assigned_to=self.developer,
            assigned_by=self.manager
        )

        self.deleted_task = Task.objects.create(
            project=self.project,
            title='Some deleted task',
            status=TaskStatus.TODO,
            priority=TaskPriority.LOW,
            is_deleted=True,
            assigned_by=self.manager
        )

        self.archived_task = Task.objects.create(
            project=self.project,
            title='Completed archived task',
            status=TaskStatus.COMPLETED,
            priority=TaskPriority.MEDIUM,
            is_archived=True,
            archived_at=timezone.now(),
            assigned_by=self.manager
        )

        # ---------------- URLS ----------------
        self.list_url = reverse('task-comment-list', kwargs={'task_slug': self.task.slug})

    # ======================================================
    # MODEL VALIDATION TESTS
    # ======================================================

    def test_model_validations(self):
        comment = TaskComment(task=self.task, author=self.developer, content="   ")
        with self.assertRaises(Exception):
            comment.full_clean()

        comment = TaskComment(task=self.deleted_task, author=self.developer, content="Hello")
        with self.assertRaises(Exception):
            comment.full_clean()

        comment = TaskComment(task=self.archived_task, author=self.developer, content="Hello")
        with self.assertRaises(Exception):
            comment.full_clean()

    # ======================================================
    # RBAC TESTS
    # ======================================================

    def test_comment_creation_rbac(self):
        data = {'content': 'Test comment'}

        self.client.force_authenticate(user=self.client_user)
        self.assertEqual(
            self.client.post(self.list_url, data).status_code,
            status.HTTP_403_FORBIDDEN
        )

        self.client.force_authenticate(user=self.other_developer)
        self.assertEqual(
            self.client.post(self.list_url, data).status_code,
            status.HTTP_403_FORBIDDEN
        )

        self.client.force_authenticate(user=self.developer)
        self.assertEqual(
            self.client.post(self.list_url, data).status_code,
            status.HTTP_201_CREATED
        )

        self.client.force_authenticate(user=self.manager)
        self.assertEqual(
            self.client.post(self.list_url, data).status_code,
            status.HTTP_201_CREATED
        )

        self.client.force_authenticate(user=self.admin)
        self.assertEqual(
            self.client.post(self.list_url, data).status_code,
            status.HTTP_201_CREATED
        )

    # ======================================================
    # EDIT TESTS
    # ======================================================

    def test_comment_editing_rbac(self):
        comment = TaskComment.objects.create(
            task=self.task,
            author=self.developer,
            content="Initial"
        )

        url = reverse('task-comment-detail', kwargs={'task_slug': self.task.slug, 'pk': comment.id})

        self.client.force_authenticate(user=self.other_developer)
        self.assertEqual(
            self.client.patch(url, {'content': 'x'}).status_code,
            status.HTTP_403_FORBIDDEN
        )

        self.client.force_authenticate(user=self.developer)
        response = self.client.patch(url, {'content': 'Updated'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        comment.refresh_from_db()
        self.assertTrue(comment.is_edited)

    # ======================================================
    # DELETE TESTS
    # ======================================================

    def test_comment_soft_delete(self):
        comment = TaskComment.objects.create(
            task=self.task,
            author=self.developer,
            content="Secret"
        )

        url = reverse('task-comment-detail', kwargs={'task_slug': self.task.slug, 'pk': comment.id})

        self.client.force_authenticate(user=self.developer)
        self.assertEqual(
            self.client.delete(url).status_code,
            status.HTTP_204_NO_CONTENT
        )

        comment.refresh_from_db()
        self.assertTrue(comment.is_deleted)

    # ======================================================
    # ACTIVITY LOG TESTS
    # ======================================================

    def test_activity_logging_integration(self):
        self.client.force_authenticate(user=self.developer)

        # CREATE
        response = self.client.post(self.list_url, {'content': 'Log me'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        log = ActivityLog.objects.filter(task=self.task).latest('created_at')
        self.assertIn("Comment", log.description)

        # UPDATE
        comment_id = response.data['id']
        url = reverse('task-comment-detail', kwargs={'task_slug': self.task.slug, 'pk': comment_id})

        self.client.patch(url, {'content': 'Updated'})

        log = ActivityLog.objects.filter(task=self.task).latest('created_at')
        self.assertIn("updated", log.description)

        # DELETE
        self.client.delete(url)

        log = ActivityLog.objects.filter(task=self.task).latest('created_at')
        self.assertIn("deleted", log.description)