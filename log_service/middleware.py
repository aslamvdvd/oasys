"""
Middleware for logging administrative actions.
"""
import logging
from django.contrib.auth import user_logged_out
from django.contrib.auth.signals import user_login_failed
from django.dispatch import receiver

# Use Enums and Constants
from .events import (
    LogEventType,
    EVENT_ADMIN_LOGIN, EVENT_ADMIN_LOGOUT, EVENT_ADMIN_LOGIN_FAILED
)
from .utils import create_log_data, match_admin_path, resolve_event_name, is_loggable_request
from .logger import log_event

logger = logging.getLogger(__name__)

@receiver(user_logged_out)
def handle_admin_logout(sender, request, user, **kwargs):
    """
    Log user logout specifically from the admin interface.
    """
    # Use constant for path check for consistency
    if user and request and request.path.startswith('/admin/logout/'):
        logger.info(f"Admin logout detected for user: {user.username}")
        log_data = create_log_data(
            event=EVENT_ADMIN_LOGOUT,
            user=user.username,
            action='logout', # Action type string
            target='admin.session',
            method=request.method,
            status=response.status_code if 'response' in kwargs else 200 # Best guess status
        )
        log_event(LogEventType.ADMIN, log_data)

@receiver(user_login_failed)
def handle_admin_login_failure(sender, credentials, request, **kwargs):
    """
    Log failed login attempts to the admin interface via signal.
    """
    if request and request.path.startswith('/admin/login/'):
        username = credentials.get('username', 'unknown')
        logger.info(f"Signal detected admin login failure for user: {username}")
        log_data = create_log_data(
            event=EVENT_ADMIN_LOGIN_FAILED,
            user=username,
            action='login_failed',
            target='admin.session',
            method=request.method,
            status=401 # Unauthorized
        )
        log_event(LogEventType.ADMIN, log_data)

class AdminActivityMiddleware:
    """
    Middleware to log admin activity using centralized utilities.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Handle Login POSTs explicitly (Success/Failure)
        if request.path.startswith('/admin/login/') and request.method == 'POST':
            self._handle_login_post(request, response)
            return response

        # Handle general loggable requests
        if is_loggable_request(request, response) and request.user.is_authenticated:
            admin_info = match_admin_path(request.path)
            if admin_info:
                self._log_general_admin_activity(request, response, admin_info)

        return response

    def _handle_login_post(self, request, response):
        """
        Handles logging for POST requests to the admin login URL.
        Logs either admin_login_failed or admin_login.
        """
        # Failed Login Fallback (Signal handler is primary)
        if not request.user.is_authenticated:
            username = request.POST.get('username', 'unknown')
            logger.info(f"Middleware fallback detected potential admin login failure for user: {username}")
            log_data = create_log_data(
                event=EVENT_ADMIN_LOGIN_FAILED,
                user=username,
                action='login_failed',
                target='admin.session',
                method=request.method,
                status=401 # Log as 401 regardless of response status
            )
            # Avoid double logging if signal already handled it (Requires coordination if needed)
            # For simplicity, we might allow potential double logs here if signal fires AND this check passes
            log_event(LogEventType.ADMIN, log_data)

        # Successful Login
        elif request.user.is_authenticated and response.status_code == 302:
            logger.info(f"Middleware detected successful admin login for user: {request.user.username}")
            log_data = create_log_data(
                event=EVENT_ADMIN_LOGIN,
                user=request.user.username,
                action='login', # Action type string
                target='admin.session',
                method=request.method,
                status=response.status_code
            )
            log_event(LogEventType.ADMIN, log_data)

    def _log_general_admin_activity(self, request, response, admin_info):
        """
        Logs general admin activity (views, edits, adds, deletes) using helpers.
        """
        action_type = admin_info['action_type'] # This is now an event constant
        event_name = resolve_event_name(action_type, request.method) # Gets the final event name

        target = f"{admin_info.get('app_label', '')}.{admin_info.get('model_name', '')}"
        target = target if target != '.' else 'admin' # Clean up target for dashboard/root

        log_data = create_log_data(
            event=event_name,
            user=request.user.username,
            action=action_type, # Log the constant representing the action group
            target=target,
            object_id=admin_info.get('object_id', ''),
            method=request.method,
            status=response.status_code
        )
        log_event(LogEventType.ADMIN, log_data)


# ----- Signal Connections (Kept in middleware.py for clarity) -----

# Ensure signals are connected. Using the @receiver decorator handles this,
# but explicit connection doesn't hurt and can be clearer for some.
# user_logged_out.connect(log_user_logout)
# user_login_failed.connect(handle_admin_login_failure)
# Note: Explicitly connecting signals decorated with @receiver can lead to duplicate signal handling.
# It's generally recommended to use one method or the other. @receiver is preferred.

# Clean up old functions that are now replaced by utils or refactored logic
# (Remove _should_log, _get_event_name, _get_admin_info from the class if they existed)