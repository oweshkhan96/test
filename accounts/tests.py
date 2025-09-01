from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import CustomUser

User = get_user_model()

class AuthTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = CustomUser.objects.create_user(
            username='admin_test',
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
            last_name='User',
            role='admin',
            company_name='Test Company'
        )
        self.driver_user = CustomUser.objects.create_user(
            username='driver_test', 
            email='driver@test.com',
            password='testpass123',
            first_name='Driver',
            last_name='User', 
            role='driver'
        )

    def test_login_page_loads(self):
        response = self.client.get(reverse('accounts:login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Login')

    def test_admin_login_redirect(self):
        response = self.client.post(reverse('accounts:login'), {
            'form_type': 'login',
            'username': 'admin_test',
            'password': 'testpass123'
        })
        self.assertRedirects(response, '/dashboard/')

    def test_driver_login_redirect(self):
        response = self.client.post(reverse('accounts:login'), {
            'form_type': 'login', 
            'username': 'driver_test',
            'password': 'testpass123'
        })
        self.assertRedirects(response, '/dashboard/driver/')

    def test_registration_creates_admin_user(self):
        response = self.client.post(reverse('accounts:register'), {
            'form_type': 'register',
            'username': 'newadmin',
            'email': 'newadmin@test.com',
            'first_name': 'New',
            'last_name': 'Admin', 
            'company_name': 'New Company',
            'password1': 'complexpass123',
            'password2': 'complexpass123'
        })
        
        user = CustomUser.objects.get(username='newadmin')
        self.assertEqual(user.role, 'admin')
        self.assertTrue(user.is_staff)
