from django.test import TestCase
from django.contrib.auth import get_user_model
from notifications.models import Notification

User = get_user_model()

class NotificationModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='dev@orbitpm.com',
            password='password123',
            full_name='Staff Developer'
        )

    def test_create_notification_successful(self):
        notification = Notification.objects.create(
            recipient=self.user,
            title='New Assignment',
            message='You have been assigned to task Alpha.',
            is_read=False
        )
        self.assertEqual(notification.recipient, self.user)
        self.assertEqual(notification.title, 'New Assignment')
        self.assertFalse(notification.is_read)
