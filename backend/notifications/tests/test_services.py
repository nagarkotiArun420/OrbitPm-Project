from django.test import TestCase
from django.contrib.auth import get_user_model
from projects.models import Project
from tasks.models import Task, TaskComment
from tasks.constants import TaskStatus
from notifications.models import Notification
from notifications.constants import NotificationType
from notifications.services import (
    create_notification,
    mark_notification_as_read,
    mark_all_notifications_as_read,
    notify_task_assignment,
    notify_task_comment,
    notify_task_completion,
    notify_project_update,
)

User = get_user_model()


class NotificationServicesTests(TestCase):
    def setUp(self):
        # Create different users
        self.admin = User.objects.create_user(
            email='admin@orbitpm.com',
            password='password123',
            full_name='Admin User',
            role=User.Roles.ADMIN
        )
        self.manager = User.objects.create_user(
            email='manager@orbitpm.com',
            password='password123',
            full_name='Manager User',
            role=User.Roles.MANAGER
        )
        self.developer1 = User.objects.create_user(
            email='dev1@orbitpm.com',
            password='password123',
            full_name='Developer One',
            role=User.Roles.DEVELOPER
        )
        self.developer2 = User.objects.create_user(
            email='dev2@orbitpm.com',
            password='password123',
            full_name='Developer Two',
            role=User.Roles.DEVELOPER
        )

        # Create project
        self.project = Project.objects.create(
            title='Project Phoenix',
            created_by=self.admin,
            manager=self.manager
        )
        self.project.team_members.add(self.developer1, self.developer2)

        # Create task
        self.task = Task.objects.create(
            project=self.project,
            title='Task Alpha',
            assigned_to=self.developer1,
            assigned_by=self.manager
        )

    def test_create_notification_success(self):
        notification = create_notification(
            recipient=self.developer1,
            actor=self.manager,
            notification_type=NotificationType.TASK_ASSIGNED,
            title="Task Assigned",
            message="You have been assigned a task.",
            metadata={"task_id": str(self.task.id)}
        )
        self.assertIsNotNone(notification)
        self.assertEqual(notification.recipient, self.developer1)
        self.assertEqual(notification.actor, self.manager)
        self.assertEqual(notification.notification_type, NotificationType.TASK_ASSIGNED)
        self.assertEqual(notification.metadata["task_id"], str(self.task.id))
        self.assertFalse(notification.is_read)
        self.assertIsNone(notification.read_at)

    def test_create_notification_suppresses_self_notification(self):
        # Users should not get notified about their own actions
        notification = create_notification(
            recipient=self.developer1,
            actor=self.developer1,
            notification_type=NotificationType.TASK_COMMENTED,
            title="Self Notification",
            message="Testing self notification suppression."
        )
        self.assertIsNone(notification)

    def test_mark_notification_as_read(self):
        notification = create_notification(
            recipient=self.developer1,
            actor=self.manager,
            notification_type=NotificationType.TASK_ASSIGNED,
            title="Task Assigned",
            message="Task assigned"
        )
        
        updated_notif = mark_notification_as_read(notification)
        self.assertTrue(updated_notif.is_read)
        self.assertIsNotNone(updated_notif.read_at)

    def test_mark_all_notifications_as_read(self):
        # Create multiple notifications
        create_notification(self.developer1, self.manager, NotificationType.TASK_ASSIGNED, "Title 1", "Message 1")
        create_notification(self.developer1, self.manager, NotificationType.TASK_ASSIGNED, "Title 2", "Message 2")
        
        # Another user's notification
        create_notification(self.developer2, self.manager, NotificationType.TASK_ASSIGNED, "Title 3", "Message 3")

        count = mark_all_notifications_as_read(self.developer1)
        self.assertEqual(count, 2)
        
        # Verify first user's notifications are read
        self.assertEqual(Notification.objects.filter(recipient=self.developer1, is_read=True).count(), 2)
        # Verify second user's notifications are still unread
        self.assertEqual(Notification.objects.filter(recipient=self.developer2, is_read=False).count(), 1)

    def test_notify_task_assignment(self):
        # Clear existing notifications
        Notification.objects.all().delete()

        # Re-assign using service
        notify_task_assignment(self.task, actor=self.manager)
        
        self.assertEqual(Notification.objects.count(), 1)
        notif = Notification.objects.first()
        self.assertEqual(notif.recipient, self.developer1)
        self.assertEqual(notif.actor, self.manager)
        self.assertEqual(notif.notification_type, NotificationType.TASK_ASSIGNED)

    def test_notify_task_comment(self):
        # Create comment
        comment = TaskComment.objects.create(
            task=self.task,
            author=self.developer1,
            content="Working on this now!"
        )
        
        # Clear any auto-generated notifications first to test service in isolation
        Notification.objects.all().delete()
        
        # Trigger comment notifications
        notify_task_comment(comment)

        # Developer1 is the author, so other stakeholders (manager, creator/admin) should get notified
        # self.task assignee is DeveloperOne, creator is Manager User, project creator is Admin User, project manager is Manager User
        # The unique stakeholders excluding the author are Manager (Manager User) and Admin (Admin User)
        recipients = Notification.objects.values_list('recipient__email', flat=True)
        self.assertEqual(len(recipients), 2)
        self.assertIn(self.manager.email, recipients)
        self.assertIn(self.admin.email, recipients)

    def test_notify_task_completion(self):
        # Mark completed
        self.task.status = TaskStatus.COMPLETED
        self.task.save()
        
        Notification.objects.all().delete()
        
        # Developer1 completed it
        notify_task_completion(self.task, actor=self.developer1)
        
        # Stakeholders to notify: Manager User (creator/project manager), Admin User (project creator)
        recipients = list(Notification.objects.values_list('recipient__email', flat=True))
        self.assertEqual(len(recipients), 2)
        self.assertIn(self.manager.email, recipients)
        self.assertIn(self.admin.email, recipients)

    def test_notify_project_update(self):
        Notification.objects.all().delete()
        
        changes = {'title': {'old': 'Old Title', 'new': 'Project Phoenix'}}
        notify_project_update(self.project, actor=self.admin, changes=changes)
        
        # Recipients: team members (dev1, dev2) and manager (manager)
        recipients = list(Notification.objects.values_list('recipient__email', flat=True))
        self.assertEqual(len(recipients), 3)
        self.assertIn(self.manager.email, recipients)
        self.assertIn(self.developer1.email, recipients)
        self.assertIn(self.developer2.email, recipients)
        self.assertNotIn(self.admin.email, recipients) # Actor excluded
