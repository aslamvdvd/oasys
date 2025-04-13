from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
from django.utils import timezone
import logging

from log_service import log_event

User = get_user_model()
logger = logging.getLogger(__name__)

class EmailOrUsernameBackend(ModelBackend):
    """
    Custom authentication backend to allow users to log in with either their email or username.
    Also logs failed login attempts to the admin interface.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            # Check if the provided credential is an email or username
            # The username parameter is used by Django's auth system, but in our form 
            # we're actually passing either an email or username into this field
            user = User.objects.get(
                Q(email__iexact=username) | Q(username__iexact=username)
            )
            
            # Check the password
            if user.check_password(password):
                return user
            
            # Password check failed - log if it's an admin login
            if request and request.path.startswith('/admin/'):
                self._log_failed_admin_login(request, username)
            return None
            
        except User.DoesNotExist:
            # User doesn't exist - log if it's an admin login
            if request and request.path and request.path.startswith('/admin/'):
                self._log_failed_admin_login(request, username)
            return None
            
    def _log_failed_admin_login(self, request, username):
        """
        Log failed admin login attempts.
        """
        logger.info(f"Admin authentication failed for user '{username}'")
        
        log_data = {
            'event': 'admin_login_failed',
            'user': username or 'unknown',
            'action': 'login_failed',
            'target': 'admin.session',
            'object_id': '',
            'method': request.method,
            'status': 401,  # Unauthorized
            'timestamp': timezone.now().isoformat()
        }
        
        log_event('admin', log_data)
            
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None 