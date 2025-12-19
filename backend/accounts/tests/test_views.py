from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

User = get_user_model()

class AuthViewTests(APITestCase):
    def setUp(self):
        self.register_url = reverse('auth_register')
        self.login_url = reverse('auth_login')
        self.me_url = reverse('auth_me')
        self.logout_url = reverse('auth_logout')
        
        self.user_data = {
            'email': 'developer@orbitpm.com',
            'full_name': 'Dev Star',
            'password': 'SecurePassword@2026',
            'confirm_password': 'SecurePassword@2026',
            'role': 'DEVELOPER'
        }
        
        # Pre-seed a user for login/profile tests
        self.active_user = User.objects.create_user(
            email='testuser@orbitpm.com',
            password='SecurePassword@2026',
            full_name='Test User',
            role=User.Roles.MANAGER
        )

    def test_register_user_successful(self):
        """
        Verify successful user registration via registration endpoint.
        """
        response = self.client.post(self.register_url, self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['email'], 'developer@orbitpm.com')
        self.assertEqual(response.data['data']['role'], 'DEVELOPER')
        self.assertIn('updated_at', response.data['data'])

    def test_register_password_mismatch(self):
        """
        Verify registration fails if passwords do not match.
        """
        data = self.user_data.copy()
        data['confirm_password'] = 'DifferentPassword@2026'
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertIn('confirm_password', response.data['error'])

    def test_register_weak_password(self):
        """
        Verify registration fails for a weak password (e.g. missing special characters or too short).
        """
        data = self.user_data.copy()
        data['password'] = 'weak123'
        data['confirm_password'] = 'weak123'
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertIn('password', response.data['error'])

    def test_login_successful(self):
        """
        Verify a registered user can login and retrieve custom JWT claims + profile.
        """
        login_payload = {
            'email': 'testuser@orbitpm.com',
            'password': 'SecurePassword@2026'
        }
        response = self.client.post(self.login_url, login_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify custom serializer includes user info and tokens
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data['user']['email'], 'testuser@orbitpm.com')
        self.assertEqual(response.data['user']['role'], 'MANAGER')

    def test_login_successful_case_insensitive(self):
        """
        Verify that logging in with an email in different casing succeeds.
        """
        login_payload = {
            'email': 'TestUser@OrbitPM.com',  # Seeded as testuser@orbitpm.com
            'password': 'SecurePassword@2026'
        }
        response = self.client.post(self.login_url, login_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertEqual(response.data['user']['email'], 'testuser@orbitpm.com')

    def test_login_invalid_credentials(self):
        """
        Verify login fails with incorrect password.
        """
        login_payload = {
            'email': 'testuser@orbitpm.com',
            'password': 'WrongPassword123'
        }
        response = self.client.post(self.login_url, login_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_profile_authenticated(self):
        """
        Verify an authenticated request can load current user profile details.
        """
        access_token = str(AccessToken.for_user(self.active_user))
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['email'], 'testuser@orbitpm.com')

    def test_retrieve_profile_unauthenticated(self):
        """
        Verify unauthenticated profile request fails.
        """
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_blacklists_token(self):
        """
        Verify that hitting logout endpoint blacklists the refresh token.
        """
        access_token = str(AccessToken.for_user(self.active_user))
        refresh_token = str(RefreshToken.for_user(self.active_user))
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        response = self.client.post(self.logout_url, {'refresh': refresh_token}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Verify subsequent refresh attempt using the same token fails
        refresh_url = reverse('auth_refresh')
        refresh_response = self.client.post(refresh_url, {'refresh': refresh_token}, format='json')
        self.assertEqual(refresh_response.status_code, status.HTTP_401_UNAUTHORIZED)
