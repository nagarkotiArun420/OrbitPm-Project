from django.test import TestCase
from django.contrib.auth import get_user_model

User = get_user_model()

class UserModelTests(TestCase):
    def test_create_user_with_email_successful(self):
        """
        Test creating a standard user with email.
        """
        user = User.objects.create_user(
            email='dev@orbitpm.com',
            password='testpassword123',
            full_name='Lead Developer',
            role=User.Roles.DEVELOPER
        )
        self.assertEqual(user.email, 'dev@orbitpm.com')
        self.assertEqual(user.full_name, 'Lead Developer')
        self.assertEqual(user.role, User.Roles.DEVELOPER)
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_superuser_successful(self):
        """
        Test creating an admin superuser.
        """
        admin_user = User.objects.create_superuser(
            email='admin@orbitpm.com',
            password='adminpassword123',
            full_name='System Admin'
        )
        self.assertEqual(admin_user.email, 'admin@orbitpm.com')
        self.assertEqual(admin_user.role, User.Roles.ADMIN)
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)
