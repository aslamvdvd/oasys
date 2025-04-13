"""
Middleware for logging administrative actions.
"""
import re
import logging
from django.urls import resolve
from django.utils import timezone
from django.contrib.auth import user_logged_out
from django.contrib.auth.signals import user_login_failed
from django.dispatch import receiver

from log_service import log_event

logger = logging.getLogger(__name__)

@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    if user and request and request.path.startswith('/admin/'):
        log_event('admin', {
            'event': 'admin_logout',
            'user': user.username,
            'action': 'logout',
            'target': 'admin.session',
            'object_id': '',
            'method': request.method,
            'status': 200,
            'timestamp': timezone.now().isoformat()
        })

@receiver(user_login_failed)
def log_user_login_failed(sender, credentials, **kwargs):
    try:
        request = kwargs.get('request')
        if request and request.path.startswith('/admin/'):
            username = credentials.get('username', '')
            log_event('admin', {
                'event': 'admin_login_failed',
                'user': username,
                'action': 'login_failed',
                'target': 'admin.session',
                'object_id': '',
                'method': request.method,
                'status': 401,
                'timestamp': timezone.now().isoformat()
            })
            logger.info(f"Logging admin login failed for user: {username}")
    except Exception as e:
        logger.error(f"Error in login_failed signal handler: {str(e)}")

class AdminActivityMiddleware:
    admin_patterns = [
        (r'^/admin/(\w+)/(\w+)/(\d+)/change/', 'edit_object'),
        (r'^/admin/(\w+)/(\w+)/(\d+)/delete/', 'delete_object'),
        (r'^/admin/(\w+)/(\w+)/add/', 'add_object'),
        (r'^/admin/(\w+)/(\w+)/', 'view_object_list'),
        (r'^/admin/login/', 'login'),
        (r'^/admin/logout/', 'logout'),
        (r'^/admin/$', 'view_dashboard'),  # Match only the exact admin root
        (r'^/admin/', 'other')  # Catch-all for anything else under admin
    ]
    skip_patterns = ['/admin/jsi18n/', '/admin/autocomplete/', '/static/', '/favicon.ico']

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Track failed login attempts
        if request.path.startswith('/admin/login/') and request.method == 'POST' and not request.user.is_authenticated and response.status_code == 200:
            username = request.POST.get('username', '')
            if username:
                logger.info(f"Detected failed admin login attempt for user: {username}")
                log_event('admin', {
                    'event': 'admin_login_failed',
                    'user': username,
                    'action': 'login_failed',
                    'target': 'admin.session',
                    'object_id': '',
                    'method': request.method,
                    'status': 401,
                    'timestamp': timezone.now().isoformat()
                })
        
        # Track successful logins (when user is authenticated and redirected)
        if request.path.startswith('/admin/login/') and request.method == 'POST' and request.user.is_authenticated and response.status_code == 302:
            logger.info(f"Detected successful admin login for user: {request.user.username}")
            log_event('admin', {
                'event': 'admin_login',
                'user': request.user.username,
                'action': 'login',
                'target': 'admin.session',
                'object_id': '',
                'method': request.method,
                'status': response.status_code,
                'timestamp': timezone.now().isoformat()
            })
            return response  # Skip further processing for login success

        if not self._should_log(request, response):
            return response

        admin_info = self._get_admin_info(request)
        if admin_info and request.user.is_authenticated:
            event_name = self._get_event_name(admin_info['action_type'], request.method)
            log_data = {
                'event': event_name,
                'user': request.user.username,
                'action': admin_info['action_type'],
                'target': f"{admin_info.get('app_label', '')}.{admin_info.get('model_name', '')}",
                'object_id': admin_info.get('object_id', ''),
                'method': request.method,
                'status': response.status_code,
                'timestamp': timezone.now().isoformat()
            }
            log_event('admin', log_data)

        return response

    def _should_log(self, request, response):
        if not request.path.startswith('/admin/'):
            return False
        if any(pattern in request.path for pattern in self.skip_patterns):
            return False
        if request.path.startswith('/admin/login/') and request.method == 'POST':
            return True
        if request.method == 'GET':
            return not re.search(r'/admin/.*\.', request.path) and response.status_code == 200
        elif request.method == 'POST':
            return response.status_code in [200, 201, 302]
        return False

    def _get_event_name(self, action_type, method):
        """
        Get a clear event name based on action type and method.
        """
        # For successful logins (POST requests)
        if method == 'POST':
            if action_type == 'add_object':
                return 'object_created'
            elif action_type == 'edit_object':
                return 'object_updated'
            elif action_type == 'delete_object':
                return 'object_deleted'
            elif action_type == 'login':
                return 'admin_login'
            elif action_type == 'logout':
                return 'admin_logout'
        # For GET requests, properly name the views
        elif method == 'GET':
            if action_type == 'view_dashboard':
                return 'admin_view_dashboard'
            elif action_type == 'login':
                return 'admin_login_page'  # Viewing the login page
            
        # Default pattern for other actions
        return f"admin_{action_type}"

    def _get_admin_info(self, request):
        path = request.path
        for pattern, action_type in self.admin_patterns:
            match = re.match(pattern, path)
            if match:
                info = {'action_type': action_type}
                groups = match.groups()
                if len(groups) >= 2:
                    info['app_label'] = groups[0]
                    info['model_name'] = groups[1]
                if len(groups) >= 3:
                    info['object_id'] = groups[2]
                return info
        if path.startswith('/admin/'):
            return {'action_type': 'other'}
        return None

user_logged_out.connect(log_user_logout)
user_login_failed.connect(log_user_login_failed)