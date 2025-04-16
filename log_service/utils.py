"""
Utility functions for the log_service app, simplifying common logging tasks.
Provides helpers to call the core `log_event` function with appropriate parameters.
"""

import re
import traceback
import logging
from typing import Optional, Dict, Any, Tuple, List

from django.http import HttpRequest
from django.conf import settings # Needed for HAS_LOG_SERVICE check

# Import Enums, Constants, and the core log_event function
from .events import (
    LogEventType,
    LogSeverity,
    EVENT_LOGIN, EVENT_LOGOUT, EVENT_LOGIN_FAILED, EVENT_USER_CREATED,
    EVENT_PROFILE_UPDATE, EVENT_ACCOUNT_DELETED, EVENT_DASHBOARD_VISIT,
    EVENT_PASSWORD_RESET_REQUEST, EVENT_PASSWORD_RESET_COMPLETE, # Added
    EVENT_PASSWORD_CHANGE, EVENT_EMAIL_CHANGE_REQUEST, EVENT_EMAIL_CHANGE_COMPLETE, # Added
    EVENT_TEMPLATE_UPLOADED, EVENT_TEMPLATE_ERROR, EVENT_TEMPLATE_DELETED,
    EVENT_ADMIN_LOGIN, EVENT_ADMIN_LOGOUT, EVENT_ADMIN_LOGIN_FAILED, EVENT_ADMIN_LOGIN_PAGE,
    EVENT_ADMIN_VIEW_DASHBOARD, EVENT_ADMIN_VIEW_OBJECT_LIST, EVENT_ADMIN_EDIT_OBJECT,
    EVENT_ADMIN_DELETE_OBJECT, EVENT_ADMIN_ADD_OBJECT, EVENT_ADMIN_OTHER,
    EVENT_OBJECT_CREATED, EVENT_OBJECT_UPDATED, EVENT_OBJECT_DELETED,
    EVENT_APP_EXCEPTION, EVENT_APP_PERMISSION_DENIED, EVENT_APP_SENSITIVE_ACTION
)
from .logger import log_event

# --- Fallback Mechanism --- 

# Use standard logging for internal utils messages
_util_logger = logging.getLogger(__name__)

# Check if the core logger is available
# This assumes log_event function itself is the indicator of availability
HAS_LOG_SERVICE = hasattr(settings, 'LOGS_DIR') and callable(log_event)

if not HAS_LOG_SERVICE:
    _util_logger.warning("Log service (log_event or LOGS_DIR) appears unavailable. Logging helpers will be no-ops.")
    # Define dummy logger function if service not found
    def _dummy_log_event(*args, **kwargs): 
        _util_logger.debug(f"Log service unavailable. Call suppressed: args={args}, kwargs={kwargs}")
    # Override log_event with the dummy
    log_event = _dummy_log_event
    
# --- NEW General Purpose Log Helpers --- 

def log_exception(
    request: Optional[HttpRequest],
    exc: Exception,
    source: str,
    user: Optional[Any] = None,
    message: Optional[str] = None,
    severity: LogSeverity = LogSeverity.ERROR,
    extra_data: Optional[Dict[str, Any]] = None
) -> None:
    """Logs an application exception with traceback."""
    if not HAS_LOG_SERVICE: return

    detail = message or f"Exception caught: {type(exc).__name__}"
    tb_str = traceback.format_exc() 

    local_extra = {
        'exception_type': type(exc).__name__,
        'exception_args': getattr(exc, 'args', None),
        'traceback': tb_str,
    }
    if extra_data:
        local_extra.update(extra_data)
        
    # Attempt to get user from request if not provided
    if user is None and request and hasattr(request, 'user') and isinstance(request.user, User) and request.user.is_authenticated:
        user = request.user
        
    log_event(
        event_type=LogEventType.APPLICATION,
        event_name=EVENT_APP_EXCEPTION,
        severity=severity,
        user=user,
        request=request,
        source=source,
        message=detail,
        extra_data=local_extra
    )

def log_permission_denied(
    request: Optional[HttpRequest],
    source: str,
    user: Optional[Any] = None,
    message: Optional[str] = None,
    target: Optional[str] = None,
    extra_data: Optional[Dict[str, Any]] = None
) -> None:
    """Logs a permission denied event."""
    if not HAS_LOG_SERVICE: return

    detail = message or "Permission denied accessing resource."
    
    # Attempt to get user from request if not provided
    if user is None and request and hasattr(request, 'user') and isinstance(request.user, User) and request.user.is_authenticated:
        user = request.user
        
    log_event(
        event_type=LogEventType.APPLICATION,
        event_name=EVENT_APP_PERMISSION_DENIED,
        severity=LogSeverity.WARNING,
        user=user,
        request=request,
        source=source,
        message=detail,
        target=target,
        extra_data=extra_data
    )

def log_sensitive_action(
    event_name: str,
    user: Optional[Any],
    source: str,
    message: str,
    request: Optional[HttpRequest] = None,
    target: Optional[str] = None,
    severity: LogSeverity = LogSeverity.INFO,
    extra_data: Optional[Dict[str, Any]] = None
) -> None:
    """
    Logs a sensitive or important application action requiring an audit trail.
    Defaults to APPLICATION event type, but caller can override via extra_data if needed.
    """
    if not HAS_LOG_SERVICE: return
    
    log_event(
        event_type=LogEventType.APPLICATION, # Default type
        event_name=event_name, # Specific event name passed in
        severity=severity,
        user=user,
        request=request,
        source=source,
        message=message,
        target=target,
        extra_data=extra_data
    )
    
# --- User Activity Log Helpers (Refactored) --- 

def log_user_activity(
    event_name: str,
    user: Optional[Any] = None,
    request: Optional[HttpRequest] = None,
    source: Optional[str] = None, # Added source
    message: Optional[str] = None,
    severity: LogSeverity = LogSeverity.INFO,
    extra_data: Optional[Dict[str, Any]] = None,
    username_fallback: Optional[str] = None # For cases like failed login
) -> None:
    """Logs a general user activity event using LogEventType.USER_ACTIVITY."""
    if not HAS_LOG_SERVICE: return
    
    # Handle anonymous user or fallback username for specific cases
    actor = user
    if not actor and username_fallback:
        # Create a simple object or dict that log_event can handle minimally
        # This avoids needing a full User object for failed login attempts.
        actor = type('DummyUser', (), {'username': username_fallback, 'is_authenticated': False})()
        
    log_event(
        event_type=LogEventType.USER_ACTIVITY,
        event_name=event_name,
        user=actor,
        request=request,
        source=source,
        message=message,
        severity=severity,
        extra_data=extra_data
    )

def log_dashboard_visit(user: Any, request: HttpRequest, source: str):
    log_user_activity(
        event_name=EVENT_DASHBOARD_VISIT, 
        user=user, 
        request=request, 
        source=source, 
        message='User visited the main dashboard'
    )

def log_profile_update(user: Any, request: HttpRequest, source: str, changes: Dict):
    log_user_activity(
        event_name=EVENT_PROFILE_UPDATE, 
        user=user, 
        request=request,
        source=source,
        message='User updated profile info',
        extra_data={'changes': changes} # Be careful with what `changes` contains
    )

def log_account_deleted(user_id: int, username: str, email: str, source: str):
    # We don't have the user object anymore, so pass details
    log_user_activity(
        event_name=EVENT_ACCOUNT_DELETED,
        source=source,
        message=f'User account permanently deleted.',
        severity=LogSeverity.WARNING,
        extra_data={
            'deleted_user_id': user_id,
            'deleted_username': username,
            'deleted_email': email
        }
        # No user object, no request typically available here
    )

def log_user_created(user: Any, source: str, request: Optional[HttpRequest] = None):
    log_user_activity(
        event_name=EVENT_USER_CREATED, 
        user=user,
        request=request,
        source=source,
        message=f'New user account created: {getattr(user, "username", "unknown")}',
        extra_data={'email': getattr(user, "email", None), 'is_staff': getattr(user, "is_staff", None)}
    )

def log_user_login(user: Any, request: HttpRequest, source: str):
    log_user_activity(
        event_name=EVENT_LOGIN, 
        user=user, 
        request=request, 
        source=source,
        message=f'User logged in successfully: {getattr(user, "username", "unknown")}'
    )

def log_user_logout(user: Any, request: Optional[HttpRequest], source: str):
    log_user_activity(
        event_name=EVENT_LOGOUT, 
        user=user, 
        request=request, 
        source=source,
        message=f'User logged out: {getattr(user, "username", "unknown")}'
    )

def log_login_failed(username_or_email: str, request: HttpRequest, source: str, reason: str = 'Invalid credentials'):
    # User object is not available for failed login
    log_user_activity(
        event_name=EVENT_LOGIN_FAILED,
        username_fallback=username_or_email, # Pass the attempted username
        request=request, 
        source=source,
        severity=LogSeverity.WARNING,
        message=f'Login attempt failed for \'{username_or_email}\' ({reason})',
        extra_data={'reason': reason}
    )

# --- Password/Email Change Helpers (NEW) --- 

def log_password_reset_request(user: Any, request: HttpRequest, source: str):
     log_user_activity(
        event_name=EVENT_PASSWORD_RESET_REQUEST,
        user=user,
        request=request,
        source=source,
        message=f'Password reset requested for {getattr(user, "username", "unknown")}'
    )

def log_password_reset_complete(user: Any, request: HttpRequest, source: str):
    log_user_activity(
        event_name=EVENT_PASSWORD_RESET_COMPLETE,
        user=user,
        request=request,
        source=source,
        message=f'Password reset completed for {getattr(user, "username", "unknown")}'
    )

def log_password_change(user: Any, request: HttpRequest, source: str):
    log_user_activity(
        event_name=EVENT_PASSWORD_CHANGE,
        user=user,
        request=request,
        source=source,
        severity=LogSeverity.WARNING, # Changed password is a notable event
        message=f'Password changed for {getattr(user, "username", "unknown")}'
    )

def log_email_change_request(user: Any, request: HttpRequest, source: str, new_email: str):
    log_user_activity(
        event_name=EVENT_EMAIL_CHANGE_REQUEST,
        user=user,
        request=request,
        source=source,
        severity=LogSeverity.WARNING,
        message=f'Email change requested for {getattr(user, "username", "unknown")} to {new_email}',
        extra_data={'new_email': new_email}
    )

def log_email_change_complete(user: Any, request: HttpRequest, source: str, old_email: str):
    log_user_activity(
        event_name=EVENT_EMAIL_CHANGE_COMPLETE,
        user=user,
        request=request,
        source=source,
        severity=LogSeverity.WARNING,
        message=f'Email change completed for {getattr(user, "username", "unknown")}',
        extra_data={'old_email': old_email, 'new_email': getattr(user, "email", None)}
    )

# --- Admin Middleware Helpers (Kept for now, but consider moving) ---
# These are used by the AdminActivityMiddleware and don't directly call log_event

ADMIN_URL_PATTERNS: List[Tuple[str, str]] = [
    (r'^/admin/(\w+)/(\w+)/(\d+)/change/?$', EVENT_ADMIN_EDIT_OBJECT),
    (r'^/admin/(\w+)/(\w+)/(\d+)/delete/?$', EVENT_ADMIN_DELETE_OBJECT),
    (r'^/admin/(\w+)/(\w+)/add/?$', EVENT_ADMIN_ADD_OBJECT),
    (r'^/admin/(\w+)/(\w+)/?$', EVENT_ADMIN_VIEW_OBJECT_LIST),
    (r'^/admin/login/?$', EVENT_ADMIN_LOGIN),
    (r'^/admin/logout/?$', EVENT_ADMIN_LOGOUT),
    (r'^/admin/?$', EVENT_ADMIN_VIEW_DASHBOARD),
    (r'^/admin/', EVENT_ADMIN_OTHER) # Catch-all must be last
]

SKIP_LOGGING_PATTERNS: List[str] = [
    '/admin/jsi18n/', '/admin/autocomplete/', '/static/', '/favicon.ico'
]

# Maps used by middleware to determine final event name based on action_type and method
POST_EVENT_MAP: Dict[str, str] = {
    EVENT_ADMIN_ADD_OBJECT: EVENT_OBJECT_CREATED,      # POST to add results in object_created
    EVENT_ADMIN_EDIT_OBJECT: EVENT_OBJECT_UPDATED,     # POST to change results in object_updated
    EVENT_ADMIN_DELETE_OBJECT: EVENT_OBJECT_DELETED,   # POST to delete results in object_deleted
    EVENT_ADMIN_LOGIN: EVENT_ADMIN_LOGIN,              # POST to login is still admin_login (success handled by view signal)
    EVENT_ADMIN_LOGOUT: EVENT_ADMIN_LOGOUT,            # POST to logout is still admin_logout (success handled by view signal)
}

GET_EVENT_MAP: Dict[str, str] = {
    EVENT_ADMIN_VIEW_DASHBOARD: EVENT_ADMIN_VIEW_DASHBOARD,
    EVENT_ADMIN_LOGIN: EVENT_ADMIN_LOGIN_PAGE,        # GET on login page is admin_login_page
    EVENT_ADMIN_VIEW_OBJECT_LIST: EVENT_ADMIN_VIEW_OBJECT_LIST,
    EVENT_ADMIN_EDIT_OBJECT: EVENT_ADMIN_EDIT_OBJECT, # GET on change page is admin_edit_object
    EVENT_ADMIN_ADD_OBJECT: EVENT_ADMIN_ADD_OBJECT,   # GET on add page is admin_add_object
    EVENT_ADMIN_DELETE_OBJECT: EVENT_ADMIN_DELETE_OBJECT, # GET on delete page is admin_delete_object
}

def match_admin_path(path: str) -> Optional[Dict[str, str]]:
    """
    Matches the request path against predefined admin URL patterns (using constants).
    Returns a dict with action_type and potentially app_label, model_name, object_id.
    """
    for pattern, action_constant in ADMIN_URL_PATTERNS:
        match = re.match(pattern, path)
        if match:
            info = {'action_type': action_constant}
            groups = match.groups()
            try:
                if action_constant in [EVENT_ADMIN_EDIT_OBJECT, EVENT_ADMIN_DELETE_OBJECT, EVENT_ADMIN_VIEW_OBJECT_LIST, EVENT_ADMIN_ADD_OBJECT]:
                    info['app_label'] = groups[0]
                    info['model_name'] = groups[1]
                if action_constant in [EVENT_ADMIN_EDIT_OBJECT, EVENT_ADMIN_DELETE_OBJECT]:
                    info['object_id'] = groups[2]
            except IndexError:
                 _util_logger.warning(f"Regex pattern '{pattern}' for '{action_constant}' matched '{path}' but captured unexpected groups: {groups}")
            return info
    return None

def resolve_admin_event_name(action_type: str, method: str) -> str:
    """
    Determines the specific event name for an admin action based on action type and HTTP method.
    Used by the middleware.
    """
    if method == 'POST':
        # Map POST actions to specific outcomes (e.g., add -> created)
        return POST_EVENT_MAP.get(action_type, action_type) 
    elif method == 'GET':
        # Map GET actions to viewing states (e.g., login -> login_page)
        return GET_EVENT_MAP.get(action_type, action_type)
    else:
        # For other methods (PUT, DELETE directly via API?), just use the base action type
        return action_type

def is_loggable_admin_request(request: HttpRequest, response) -> bool:
    """
    Determines if the given admin request/response should be logged by the middleware.
    Focuses on general page views and actions, excluding assets and failed requests.
    Login/logout success/failure logging is typically handled via signals or view logic.
    """
    path = request.path
    method = request.method
    status_code = response.status_code

    # Basic check: must be an admin path
    if not path.startswith('/admin/'):
        return False

    # Skip non-essential patterns
    if any(pattern in path for pattern in SKIP_LOGGING_PATTERNS):
        return False
        
    # Ignore OPTIONS requests (CORS preflight)
    if method == 'OPTIONS':
        return False

    # Generally log successful (2xx) or redirect (3xx) responses for admin views/actions
    # We exclude login/logout paths here as they are better handled by specific signals/views
    # to capture success/failure accurately.
    if path.startswith('/admin/login/') or path.startswith('/admin/logout/'):
        return False
        
    # Consider successful GETs and successful/redirecting POSTs as generally loggable
    if method == 'GET' and status_code < 400:
        # Avoid logging asset-like URLs within admin
        if re.search(r'/admin/.*\.', path):
            return False
        return True
    elif method == 'POST' and status_code < 400:
        return True

    # Default: Don't log unsuccessful requests or other methods here
    return False

# --- Deprecated Helpers (to be removed or refactored if still used elsewhere) ---
# `create_base_log_data` and `create_log_data` are effectively replaced by the logic 
# within `log_event` and the new helper functions.

