from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from notifications.constants import NotificationType
from notifications.models import Notification, NotificationPreference
from notifications.services import send_in_app_notification


User = get_user_model()


class NotificationPreferenceTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='dev@orbitpm.com',
            password='password123',
            full_name='Dev User',
            role=User.Roles.DEVELOPER,
        )
        self.url = reverse('notification-preferences')

    def test_default_preferences_created_for_new_users(self):
        self.assertTrue(NotificationPreference.objects.filter(user=self.user).exists())

    def test_retrieve_preferences(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data['data']
        self.assertIn('task_assignment_enabled', data)
        self.assertIn('invitation_enabled', data)

    def test_update_preferences(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(self.url, {'task_assignment_enabled': False})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        prefs = NotificationPreference.objects.get(user=self.user)
        self.assertFalse(prefs.task_assignment_enabled)

    def test_send_in_app_notification_respects_preferences(self):
        prefs = NotificationPreference.objects.get(user=self.user)
        prefs.task_assignment_enabled = False
        prefs.save(update_fields=['task_assignment_enabled'])

        notification = send_in_app_notification(
            recipient=self.user,
            title='Assignment',
            message='Assigned to task',
            notification_type=NotificationType.TASK_ASSIGNED,
        )

        self.assertIsNone(notification)
        self.assertEqual(Notification.objects.filter(recipient=self.user).count(), 0)

