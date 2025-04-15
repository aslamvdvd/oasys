from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
import logging

# Use Enum/Constants for events
try:
    from log_service.logger import log_event # Use logger directly
    from log_service.events import LogEventType, EVENT_ADMIN_LOGIN_FAILED
    from log_service.utils import create_log_data # Original helper
    HAS_LOG_SERVICE = True
except ImportError:
    HAS_LOG_SERVICE = False
    def create_log_data(**kwargs): return kwargs
    def log_event(channel, data): pass

User = get_user_model()
logger = logging.getLogger(__name__)

class EmailOrUsernameBackend(ModelBackend):
    """
    Custom authentication backend:
    - Allows login with either email or username.
    - Logs failed admin login attempts using LogEventType.ADMIN.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authenticates a user via email or username and logs admin failures.
        """
        if not username:
            return None
        
        user = self._get_user_by_username_or_email(username)
        
        if user:
            if user.check_password(password):
                # Successful authentication
                return user
            else:
                # Password check failed
                if self._is_admin_login_attempt(request):
                    self._log_failed_admin_login(request, username)
                return None
        else:
            # User does not exist
            if self._is_admin_login_attempt(request):
                self._log_failed_admin_login(request, username)
            return None

    def _get_user_by_username_or_email(self, identifier):
        """Fetches user by username or email, case-insensitive."""
        try:
            return User.objects.get(
                Q(username__iexact=identifier) | Q(email__iexact=identifier)
            )
        except User.DoesNotExist:
            return None
        except User.MultipleObjectsReturned:
            # Handle cases where identifier might match multiple users (e.g., same email used as username)
            # Depending on policy, you might return None or log an error.
            logger.error(f"Multiple users found for identifier: {identifier}")
            return None
            
    def _is_admin_login_attempt(self, request) -> bool:
        """Checks if the request is likely an admin login attempt."""
        return request and request.path and request.path.startswith('/admin/')

    def _log_failed_admin_login(self, request, username):
        """
        Logs failed admin login attempts using the standardized helper and Enum.
        """
        logger.info(f"Admin authentication failed via backend for user: '{username}'")
        
        if HAS_LOG_SERVICE:
            log_data = create_log_data(
                event=EVENT_ADMIN_LOGIN_FAILED,
                user=username or 'unknown',
                action='login_failed', # Action type string
                target='admin.session',
                method=request.method if request else 'unknown',
                status=401, # Unauthorized
                object_id=''
            )
            # Use the LogEventType Enum here
            log_event(LogEventType.ADMIN, log_data)
        else:
            # Fallback if log_service not available
            logger.warning(f"Log service not available. Failed admin login for '{username}' not sent to central log.")
            
    def get_user(self, user_id):
        """
        Standard Django method to retrieve a user by ID.
        """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None 