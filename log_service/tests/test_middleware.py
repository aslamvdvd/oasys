"""
Tests for the log_service middleware.
"""
from unittest import mock
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_login_failed
from django.urls import reverse
from log_service.middleware import log_user_login_failed

User = get_user_model()

class AdminLoginFailedTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        # Create a regular user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password123'
        )

    @mock.patch('log_service.middleware.log_event')
    def test_login_failed_signal_admin_path(self, mock_log_event):
        """Test that admin login failures are logged when on admin path."""
        # Create a request with admin path
        request = self.factory.post('/admin/login/')
        
        # Trigger the login failed signal manually
        credentials = {'username': 'wronguser', 'password': 'wrongpass'}
        user_login_failed.send(
            sender=self.__class__,
            credentials=credentials,
            request=request
        )
        
        # Check if log_event was called with the right parameters
        mock_log_event.assert_called_once()
        args = mock_log_event.call_args[0]
        self.assertEqual(args[0], 'admin')  # First arg should be 'admin'
        
        # Check the log data
        log_data = mock_log_event.call_args[0][1]
        self.assertEqual(log_data['event'], 'admin_login_failed')
        self.assertEqual(log_data['user'], 'wronguser')
        self.assertEqual(log_data['action'], 'login_failed')

    @mock.patch('log_service.middleware.log_event')
    def test_login_failed_middleware_detection(self, mock_log_event):
        """Test that the middleware detects admin login failures."""
        # Since we can't directly test the middleware in isolation,
        # we'll make a real login attempt to a non-existent user
        response = self.client.post(
            '/admin/login/',
            {'username': 'nonexistent', 'password': 'wrongpass'}
        )
        
        # Check if the log_event was called
        self.assertTrue(mock_log_event.called)
        
        # Find the call for admin_login_failed
        admin_login_failed_call = None
        for call in mock_log_event.call_args_list:
            if call[0][1].get('event') == 'admin_login_failed':
                admin_login_failed_call = call
                break
                
        self.assertIsNotNone(admin_login_failed_call, 
                            "No admin_login_failed event was logged")
        
        if admin_login_failed_call:
            log_data = admin_login_failed_call[0][1]
            self.assertEqual(log_data['user'], 'nonexistent')
            self.assertEqual(log_data['action'], 'login_failed') 