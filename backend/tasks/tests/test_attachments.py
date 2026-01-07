import os
import uuid
import mimetypes
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from common.models import ActivityLog
from projects.constants import ProjectStatus, ProjectPriority
from projects.models import Project
from tasks.constants import TaskStatus, TaskPriority
from tasks.models import Task, TaskAttachment
from tasks.services import create_attachment, delete_attachment

User = get_user_model()


class TaskAttachmentTests(APITestCase):
    """
    Comprehensive tests for the Task Attachment system including model validations,
    API CRUD functionality, role-based access control (RBAC), and activity logging.
    """

    def setUp(self):
        # Create users
        self.admin = User.objects.create_user(
            email='admin@orbitpm.com', password='password123', full_name='Admin Boss', role=User.Roles.ADMIN
        )
        self.manager = User.objects.create_user(
            email='manager@orbitpm.com', password='password123', full_name='Manager Jack', role=User.Roles.MANAGER
        )
        self.other_manager = User.objects.create_user(
            email='other_manager@orbitpm.com', password='password123', full_name='Manager Jill', role=User.Roles.MANAGER
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

        # Create Projects
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
            title='Implement task attachments backend',
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
        self.list_url = reverse('task-attachment-list', kwargs={'task_slug': self.task.slug})

    def test_model_validations(self):
        # 1. Allowed file formats (PDF, PNG, etc.) should pass
        valid_file = SimpleUploadedFile("document.pdf", b"pdf content", content_type="application/pdf")
        attachment = create_attachment(task=self.task, uploaded_by=self.developer, file=valid_file)
        self.assertEqual(attachment.original_filename, "document.pdf")
        self.assertEqual(attachment.mime_type, "application/pdf")
        self.assertEqual(attachment.file_size, len(b"pdf content"))
        
        # Cleanup file
        if attachment.file:
            attachment.file.delete(save=False)

        # 2. Unsupported extension should raise ValidationError
        invalid_ext_file = SimpleUploadedFile("payload.exe", b"malicious binary", content_type="application/octet-stream")
        with self.assertRaises(ValidationError) as context:
            create_attachment(task=self.task, uploaded_by=self.developer, file=invalid_ext_file)
        self.assertIn("File extension '.exe' is not allowed", str(context.exception))

        # 3. Unsupported MIME type should raise ValidationError
        invalid_mime_file = SimpleUploadedFile("test.png", b"fake png content", content_type="application/x-executable")
        with self.assertRaises(ValidationError) as context:
            create_attachment(task=self.task, uploaded_by=self.developer, file=invalid_mime_file)
        self.assertIn("MIME type 'application/x-executable' is not allowed", str(context.exception))

        # 4. File exceeding max size (10MB) should raise ValidationError
        oversized_file = SimpleUploadedFile("huge.pdf", b"pdf content", content_type="application/pdf")
        oversized_file.size = 11 * 1024 * 1024  # 11MB
        with self.assertRaises(ValidationError) as context:
            create_attachment(task=self.task, uploaded_by=self.developer, file=oversized_file)
        self.assertIn("File size exceeds the maximum limit of 10MB", str(context.exception))

        # 5. Soft-deleted tasks cannot receive uploads
        with self.assertRaises(ValidationError) as context:
            create_attachment(task=self.deleted_task, uploaded_by=self.developer, file=valid_file)
        self.assertIn("Cannot upload attachments to a deleted task", str(context.exception))

        # 6. Archived tasks cannot receive uploads
        with self.assertRaises(ValidationError) as context:
            create_attachment(task=self.archived_task, uploaded_by=self.developer, file=valid_file)
        self.assertIn("Cannot upload attachments to an archived task", str(context.exception))

    def test_upload_attachment_rbac(self):
        valid_file_data = {
            'file': SimpleUploadedFile("design.png", b"image bytes", content_type="image/png")
        }

        # 1. Unauthenticated user - should get 401
        self.client.force_authenticate(user=None)
        response = self.client.post(self.list_url, valid_file_data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Reset file pointer for next requests
        valid_file_data['file'].seek(0)

        # 2. Client user - should get 403 (Forbidden)
        self.client.force_authenticate(user=self.client_user)
        response = self.client.post(self.list_url, valid_file_data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        valid_file_data['file'].seek(0)

        # 3. Unassigned developer - should get 403 (Forbidden)
        self.client.force_authenticate(user=self.other_developer)
        response = self.client.post(self.list_url, valid_file_data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        valid_file_data['file'].seek(0)

        # 4. Non-project manager - should get 403 (Forbidden)
        self.client.force_authenticate(user=self.other_manager)
        response = self.client.post(self.list_url, valid_file_data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        valid_file_data['file'].seek(0)

        # 5. Assigned developer - should get 201 (Created)
        self.client.force_authenticate(user=self.developer)
        response = self.client.post(self.list_url, valid_file_data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['original_filename'], "design.png")
        self.assertEqual(response.data['mime_type'], "image/png")

        # Cleanup uploaded file
        uploaded_id = response.data['id']
        attachment = TaskAttachment.objects.get(id=uploaded_id)
        if attachment.file:
            attachment.file.delete(save=False)
        attachment.delete()

        valid_file_data['file'].seek(0)

        # 6. Project manager - should get 201 (Created)
        self.client.force_authenticate(user=self.manager)
        response = self.client.post(self.list_url, valid_file_data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        uploaded_id = response.data['id']
        attachment = TaskAttachment.objects.get(id=uploaded_id)
        if attachment.file:
            attachment.file.delete(save=False)
        attachment.delete()

        valid_file_data['file'].seek(0)

        # 7. Admin - should get 201 (Created)
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(self.list_url, valid_file_data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        uploaded_id = response.data['id']
        attachment = TaskAttachment.objects.get(id=uploaded_id)
        if attachment.file:
            attachment.file.delete(save=False)
        attachment.delete()

    def test_list_attachments_rbac(self):
        # Create an attachment to list
        valid_file = SimpleUploadedFile("report.csv", b"csv data", content_type="text/csv")
        attachment = create_attachment(task=self.task, uploaded_by=self.developer, file=valid_file)

        # 1. Unauthenticated user -> 401
        self.client.force_authenticate(user=None)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # 2. Client user (has access to project) -> 200 OK (read-only)
        self.client.force_authenticate(user=self.client_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['data']['results']), 1)
        self.assertEqual(response.data['data']['results'][0]['original_filename'], "report.csv")

        # 3. Unassigned developer (no task access) -> 403/404 (because task itself is unauthorized)
        self.client.force_authenticate(user=self.other_developer)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # 4. Assigned developer -> 200 OK
        self.client.force_authenticate(user=self.developer)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Cleanup
        if attachment.file:
            attachment.file.delete(save=False)
        attachment.delete()

    def test_delete_attachment_rbac(self):
        # Create attachment
        valid_file = SimpleUploadedFile("readme.txt", b"some text", content_type="text/plain")
        attachment = create_attachment(task=self.task, uploaded_by=self.developer, file=valid_file)
        
        detail_url = reverse('task-attachment-detail', kwargs={'task_slug': self.task.slug, 'pk': attachment.id})

        # 1. Other developer try to delete -> 403 Forbidden
        self.client.force_authenticate(user=self.other_developer)
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # 2. Project Manager deletes -> 204 No Content
        self.client.force_authenticate(user=self.manager)
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify DB and file are deleted
        self.assertFalse(TaskAttachment.objects.filter(id=attachment.id).exists())

    def test_upload_to_invalid_tasks(self):
        valid_file_data = {
            'file': SimpleUploadedFile("doc.pdf", b"pdf content", content_type="application/pdf")
        }

        # 1. Soft-deleted task -> 404 Not Found (filtered from get_authorized_tasks querysets)
        deleted_task_url = reverse('task-attachment-list', kwargs={'task_slug': self.deleted_task.slug})
        self.client.force_authenticate(user=self.manager)
        response = self.client.post(deleted_task_url, valid_file_data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        valid_file_data['file'].seek(0)

        # 2. Archived task -> 400 Bad Request during save / clean validations
        archived_task_url = reverse('task-attachment-list', kwargs={'task_slug': self.archived_task.slug})
        response = self.client.post(archived_task_url, valid_file_data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Cannot upload attachments to an archived task", response.data['error']['file'][0])

    def test_activity_logging_integration(self):
        valid_file_data = {
            'file': SimpleUploadedFile("logs.txt", b"logs content", content_type="text/plain")
        }

        # 1. Activity log on attachment upload
        self.client.force_authenticate(user=self.developer)
        response = self.client.post(self.list_url, valid_file_data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        attachment_id = response.data['id']
        log = ActivityLog.objects.filter(target_type='TASK', target_id=str(self.task.id)).latest('created_at')
        self.assertEqual(log.actor, self.developer)
        self.assertIn("Attachment 'logs.txt' was uploaded to task", log.description)

        # 2. Activity log on attachment delete
        detail_url = reverse('task-attachment-detail', kwargs={'task_slug': self.task.slug, 'pk': attachment_id})
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        log = ActivityLog.objects.filter(target_type='TASK', target_id=str(self.task.id)).latest('created_at')
        self.assertEqual(log.actor, self.developer)
        self.assertIn("Attachment 'logs.txt' was deleted from task", log.description)
