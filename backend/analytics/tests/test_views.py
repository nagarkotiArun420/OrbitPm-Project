from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()

class AnalyticsViewsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='manager@orbitpm.com',
            password='password123',
            full_name='Agency Manager',
            role=User.Roles.MANAGER
        )
        self.client.force_authenticate(user=self.user)

    def test_get_dashboard_analytics_successful(self):
        url = reverse('analytics_dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Standard JSON renderer is used
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['total_projects'], 0)
