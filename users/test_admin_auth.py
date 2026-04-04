from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from users.models import User, UserRole

class AdminAuthTests(APITestCase):
    def setUp(self):
        self.register_url = reverse('auth_register')
        self.admin_register_url = reverse('auth_admin_register')
        self.login_url = reverse('auth_login')
        self.admin_login_url = reverse('auth_admin_login')
        
        self.admin_data = {
            'email': 'admin@example.com',
            'username': 'adminuser',
            'password': 'AdminPassword123!',
            'password2': 'AdminPassword123!',
            'first_name': 'Admin',
            'last_name': 'User'
        }
        
        self.user_data = {
            'email': 'user@example.com',
            'username': 'regularuser',
            'password': 'UserPassword123!',
            'password2': 'UserPassword123!',
            'role': UserRole.CUSTOMER
        }

    def test_admin_registration(self):
        """Test that a user can register as an admin via the dedicated endpoint"""
        response = self.client.post(self.admin_register_url, self.admin_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)
        user = User.objects.get(email='admin@example.com')
        self.assertEqual(user.role, UserRole.ADMIN)
        self.assertTrue(user.is_staff)
        self.assertEqual(user.verification_status, 'verified')

    def test_prevent_admin_role_in_standard_registration(self):
        """Test that the admin role cannot be selected in the standard registration endpoint"""
        data = self.user_data.copy()
        data['role'] = UserRole.ADMIN
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('role', response.data)

    def test_admin_login(self):
        """Test that an admin can login via the dedicated admin login endpoint"""
        # First register an admin
        self.client.post(self.admin_register_url, self.admin_data)
        
        # Now login
        login_data = {
            'email': 'admin@example.com',
            'password': 'AdminPassword123!'
        }
        response = self.client.post(self.admin_login_url, login_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertEqual(response.data['user']['role'], UserRole.ADMIN)

    def test_regular_user_cannot_use_admin_login(self):
        """Test that a regular user cannot login via the admin login endpoint"""
        # Register a regular user
        self.client.post(self.register_url, self.user_data)
        
        # Try to login via admin endpoint
        login_data = {
            'email': 'user@example.com',
            'password': 'UserPassword123!'
        }
        response = self.client.post(self.admin_login_url, login_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
