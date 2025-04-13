"""
Middleware for logging administrative actions.
"""
import re
from django.urls import resolve
from django.utils import timezone

from log_service import log_event

class AdminActivityMiddleware:
    """
    Middleware to log admin activity and page access.
    
    This middleware tracks access to admin pages and logs it to admin.log
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Admin URL patterns to track (more specific ones first)
        self.admin_patterns = [
            (r'^/admin/(\w+)/(\w+)/(\d+)/change/', 'view_edit_form'),
            (r'^/admin/(\w+)/(\w+)/(\d+)/delete/', 'view_delete_form'),
            (r'^/admin/(\w+)/(\w+)/add/', 'view_add_form'),
            (r'^/admin/(\w+)/(\w+)/', 'view_object_list'),
            (r'^/admin/$', 'view_admin_index'),
            (r'^/admin/login/', 'admin_login')
        ]
        
    def __call__(self, request):
        # Skip logging for static files, AJAX, etc.
        if not self._should_log(request):
            return self.get_response(request)
        
        # Check if the request path matches admin patterns
        admin_info = self._get_admin_info(request)
        
        # Process the request and get the response
        response = self.get_response(request)
        
        # Log admin activity if relevant
        if admin_info and request.user.is_authenticated:
            log_data = {
                'event': 'admin_access',
                'user_id': request.user.id,
                'username': request.user.username,
                'path': request.path,
                'method': request.method,
                'action_type': admin_info['action_type'],
                'app_label': admin_info.get('app_label', ''),
                'model_name': admin_info.get('model_name', ''),
                'object_id': admin_info.get('object_id', ''),
                'status_code': response.status_code,
                'timestamp': timezone.now().isoformat()
            }
            
            log_event('admin', log_data)
        
        return response
    
    def _should_log(self, request):
        """
        Determine if we should log this request.
        Skip static files, AJAX requests, etc.
        """
        # Skip if not an admin URL
        if not request.path.startswith('/admin/'):
            return False
        
        # Skip jsi18n requests
        if '/admin/jsi18n/' in request.path:
            return False
        
        # Skip static file requests
        if '/static/' in request.path:
            return False
        
        # Skip API and AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return False
        
        return True
    
    def _get_admin_info(self, request):
        """
        Extract information about the admin action from the request path.
        
        Returns:
            dict with action_type and other relevant info, or None if not an admin URL
        """
        path = request.path
        
        for pattern, action_type in self.admin_patterns:
            match = re.match(pattern, path)
            if match:
                info = {'action_type': action_type}
                
                # Extract app_label, model_name, and object_id if available
                if len(match.groups()) >= 2:
                    info['app_label'] = match.group(1)
                    info['model_name'] = match.group(2)
                
                if len(match.groups()) >= 3:
                    info['object_id'] = match.group(3)
                
                return info
        
        # If we get here, it's an admin URL we're not specifically tracking
        if path.startswith('/admin/'):
            return {'action_type': 'other_admin_access'}
        
        return None 