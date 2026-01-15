from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.utils import timezone
from projects.models import Project
from projects.constants import ProjectStatus, ProjectPriority
from tasks.models import Task, TaskComment
from tasks.constants import TaskStatus, TaskPriority
from common.models import ActivityLog

User = get_user_model()


class TaskCommentTests(APITestCase):
    """
    Integration and unit tests for the Task Comment system, permissions,
    validations, soft-deletes, and activity logging.
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
        self.other_developer = User.objects.create_user(
            email='other_dev@orbitpm.com', password='password123', full_name='Dev Joe', role=User.Roles.DEVELOPER
        )
        self.client_user = User.objects.create_user(
            email='client@orbitpm.com', password='password123', full_name='Client Bob', role=User.Roles.CLIENT
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
        self.project.team_members.add(self.other_developer)
        self.project.client = self.client_user
        self.project.save()

        # Create Tasks
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

        # URLs
        self.list_url = reverse('task-comment-list', kwargs={'task_slug': self.task.slug})

    def test_model_validations(self):
        # 1. Empty comments are invalid
        comment = TaskComment(task=self.task, author=self.developer, content="   ")
        with self.assertRaises(ValidationError) as context:
            comment.full_clean()
        self.assertIn("Comment content cannot be empty", str(context.exception))

        # 2. Deleted tasks cannot receive comments
        comment = TaskComment(task=self.deleted_task, author=self.developer, content="Hello")
        with self.assertRaises(ValidationError) as context:
            comment.full_clean()
        self.assertIn("Cannot add comments to a deleted task", str(context.exception))

        # 3. Archived tasks cannot receive new comments
        comment = TaskComment(task=self.archived_task, author=self.developer, content="New comment")
        with self.assertRaises(ValidationError) as context:
            comment.full_clean()
        self.assertIn("Cannot add new comments to an archived task", str(context.exception))

    def test_comment_creation_rbac(self):
        comment_data = {'content': 'This is a test comment.'}

        # 1. Client user - should be Forbidden (403)
        self.client.force_authenticate(user=self.client_user)
        response = self.client.post(self.list_url, comment_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # 2. Unassigned developer - should be Forbidden (403) since developer is not assigned to task
        self.client.force_authenticate(user=self.other_developer)
        response = self.client.post(self.list_url, comment_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # 3. Assigned developer - should succeed (201)
        self.client.force_authenticate(user=self.developer)
        response = self.client.post(self.list_url, comment_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['content'], 'This is a test comment.')

        # 4. Manager of project - should succeed (201)
        self.client.force_authenticate(user=self.manager)
        response = self.client.post(self.list_url, comment_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # 5. Admin - should succeed (201)
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(self.list_url, comment_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_comment_editing_rbac(self):
        # Create comment
        comment = TaskComment.objects.create(task=self.task, author=self.developer, content="Initial text")
        detail_url = reverse('task-comment-detail', kwargs={'task_slug': self.task.slug, 'pk': comment.id})

        # 1. Other developer try to edit -> Forbidden (403)
        self.client.force_authenticate(user=self.other_developer)
        response = self.client.patch(detail_url, {'content': 'Edited by hack.'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # 2. Project manager try to edit -> Forbidden (403) (only authors can edit comments)
        self.client.force_authenticate(user=self.manager)
        response = self.client.patch(detail_url, {'content': 'Edited by manager.'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # 3. Author developer edit -> Success (200)
        self.client.force_authenticate(user=self.developer)
        response = self.client.patch(detail_url, {'content': 'Edited by author.'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        comment.refresh_from_db()
        self.assertEqual(comment.content, 'Edited by author.')
        self.assertTrue(comment.is_edited)
        self.assertIsNotNone(comment.edited_at)

    def test_comment_soft_delete(self):
        comment = TaskComment.objects.create(task=self.task, author=self.developer, content="Original secret comment")
        detail_url = reverse('task-comment-detail', kwargs={'task_slug': self.task.slug, 'pk': comment.id})

        # 1. Author developer deletes own comment -> Success (204)
        self.client.force_authenticate(user=self.developer)
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify it is soft-deleted, but remains in database
        comment.refresh_from_db()
        self.assertTrue(comment.is_deleted)
        self.assertEqual(comment.content, "Original secret comment")  # DB content intact

        # Verify serialized content is masked
        response = self.client.get(detail_url)
        self.assertEqual(response.data['content'], "This comment was deleted.")
        self.assertTrue(response.data['is_deleted'])

        # 2. Manager deleting developer comment in their managed project -> Success (204)
        comment2 = TaskComment.objects.create(task=self.task, author=self.developer, content="Another comment")
        detail_url2 = reverse('task-comment-detail', kwargs={'task_slug': self.task.slug, 'pk': comment2.id})
        self.client.force_authenticate(user=self.manager)
        response = self.client.delete(detail_url2)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        comment2.refresh_from_db()
        self.assertTrue(comment2.is_deleted)

    def test_activity_logging_integration(self):
        # 1. Activity log on comment creation
        self.client.force_authenticate(user=self.developer)
        response = self.client.post(self.list_url, {'content': 'Log this please.'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        log = ActivityLog.objects.filter(target_type='TASK', target_id=str(self.task.id)).latest('created_at')
        self.assertEqual(log.actor, self.developer)
        self.assertIn("Comment added to task", log.description)

        # 2. Activity log on comment update
        comment_id = response.data['id']
        detail_url = reverse('task-comment-detail', kwargs={'task_slug': self.task.slug, 'pk': comment_id})
        response = self.client.patch(detail_url, {'content': 'Updated log.'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        log = ActivityLog.objects.filter(target_type='TASK', target_id=str(self.task.id)).latest('created_at')
        self.assertEqual(log.actor, self.developer)
        self.assertIn("Comment on task", log.description)
        self.assertIn("was updated", log.description)

        # 3. Activity log on comment delete
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        log = ActivityLog.objects.filter(target_type='TASK', target_id=str(self.task.id)).latest('created_at')
        self.assertEqual(log.actor, self.developer)
        self.assertIn("Comment on task", log.description)
        self.assertIn("was deleted", log.description)
