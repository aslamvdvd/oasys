"""
Utility functions for the log_service app, using Enums and Constants for events.
"""
import re
from django.utils import timezone
from typing import Optional, Dict, Any, Tuple, List, Union
from django.contrib.auth import get_user_model

# Import Enums, Constants, and log_event function
from .events import (
    LogEventType,
    EVENT_LOGIN, EVENT_LOGOUT, EVENT_LOGIN_FAILED, EVENT_USER_CREATED,
    EVENT_PROFILE_UPDATE, EVENT_ACCOUNT_DELETED, EVENT_DASHBOARD_VISIT,
    EVENT_TEMPLATE_UPLOADED, EVENT_TEMPLATE_ERROR, EVENT_TEMPLATE_DELETED, # Used by templator utils
    EVENT_ADMIN_ADDED, EVENT_ADMIN_CHANGED, EVENT_ADMIN_DELETED, EVENT_ADMIN_ACCESS,
    EVENT_ADMIN_LOGIN, EVENT_ADMIN_LOGOUT, EVENT_ADMIN_LOGIN_FAILED, EVENT_ADMIN_LOGIN_PAGE,
    EVENT_ADMIN_VIEW_DASHBOARD, EVENT_ADMIN_VIEW_OBJECT_LIST, EVENT_ADMIN_EDIT_OBJECT,
    EVENT_ADMIN_DELETE_OBJECT, EVENT_ADMIN_ADD_OBJECT, EVENT_ADMIN_OTHER,
    EVENT_OBJECT_CREATED, EVENT_OBJECT_UPDATED, EVENT_OBJECT_DELETED
)
from .logger import log_event # Import the refactored log_event

# Try to determine if log_service is effectively available (for fallback logic)
# This check might be simplified if log_event itself handles unavailability gracefully
# For now, keep a similar check as other modules
try:
    # Attempting import implies it *should* be available if this module is used
    from . import logger as _ # Check if logger module loads
    HAS_LOG_SERVICE = True
except ImportError:
    HAS_LOG_SERVICE = False
    # Define dummy logger if service not found
    import logging
    _fallback_logger = logging.getLogger(__name__)
    def _dummy_log_event(channel, data): _fallback_logger.warning(f"Log service unavailable. Event: {channel}, Data: {data}")
    # Override log_event if it failed to import
    log_event = _dummy_log_event

User = get_user_model()

# --- Constants (Moved from middleware, now using Event Constants) ---

ADMIN_URL_PATTERNS: List[Tuple[str, str]] = [
    (r'^/admin/(\w+)/(\w+)/(\d+)/change/', EVENT_ADMIN_EDIT_OBJECT),
    (r'^/admin/(\w+)/(\w+)/(\d+)/delete/', EVENT_ADMIN_DELETE_OBJECT),
    (r'^/admin/(\w+)/(\w+)/add/', EVENT_ADMIN_ADD_OBJECT),
    (r'^/admin/(\w+)/(\w+)/$', EVENT_ADMIN_VIEW_OBJECT_LIST), # Use constant
    (r'^/admin/login/', EVENT_ADMIN_LOGIN), # Use constant
    (r'^/admin/logout/', EVENT_ADMIN_LOGOUT), # Use constant
    (r'^/admin/$', EVENT_ADMIN_VIEW_DASHBOARD), # Use constant
    (r'^/admin/', EVENT_ADMIN_OTHER) # Use constant
]

SKIP_LOGGING_PATTERNS: List[str] = [
    '/admin/jsi18n/', '/admin/autocomplete/', '/static/', '/favicon.ico'
]

# Revised maps using constants
POST_EVENT_MAP: Dict[str, str] = {
    EVENT_ADMIN_ADD_OBJECT: EVENT_OBJECT_CREATED,
    EVENT_ADMIN_EDIT_OBJECT: EVENT_OBJECT_UPDATED,
    EVENT_ADMIN_DELETE_OBJECT: EVENT_OBJECT_DELETED,
    EVENT_ADMIN_LOGIN: EVENT_ADMIN_LOGIN, # Login action maps to login event
    EVENT_ADMIN_LOGOUT: EVENT_ADMIN_LOGOUT, # Logout action maps to logout event
}

GET_EVENT_MAP: Dict[str, str] = {
    EVENT_ADMIN_VIEW_DASHBOARD: EVENT_ADMIN_VIEW_DASHBOARD,
    EVENT_ADMIN_LOGIN: EVENT_ADMIN_LOGIN_PAGE,
    EVENT_ADMIN_VIEW_OBJECT_LIST: EVENT_ADMIN_VIEW_OBJECT_LIST,
    EVENT_ADMIN_EDIT_OBJECT: EVENT_ADMIN_EDIT_OBJECT, # Viewing edit page
    EVENT_ADMIN_ADD_OBJECT: EVENT_ADMIN_ADD_OBJECT, # Viewing add page
    EVENT_ADMIN_DELETE_OBJECT: EVENT_ADMIN_DELETE_OBJECT, # Viewing delete confirmation
}

# --- General Log Data Creation ---

def create_base_log_data(
    event: str,
    user: Optional[User] = None,
    username: Optional[str] = None,
    **extra_data
) -> Dict[str, Any]:
    """
    Creates a base dictionary for log entries with common fields.
    Prioritizes User object for details if provided.
    """
    log_data = {
        'event': event,
        'timestamp': timezone.now().isoformat(),
        **extra_data
    }
    
    final_username = 'anonymous'
    user_id = None
    email = None
    
    if user and isinstance(user, User):
        final_username = user.username
        user_id = user.id
        email = user.email
    elif username:
        final_username = username
    
    log_data.update({
        'user_id': user_id,
        'username': final_username,
        'email': email, # Include email if user object provided
    })
    
    # Remove None values for cleaner logs
    return {k: v for k, v in log_data.items() if v is not None}

# --- Admin Log Helpers --- 
# (create_admin_log_data renamed back to original create_log_data for middleware compatibility)
# (match_admin_path, resolve_event_name, is_loggable_request updated)

def create_log_data(
    event: str,
    user: str, # Middleware expects username string here
    action: str,
    target: str,
    method: Optional[str] = None,
    status: Optional[int] = None,
    object_id: str = '',
) -> Dict[str, Any]:
    """
    Creates a standardized dictionary for admin log entries (compatible with middleware usage).
    """
    # Use the base creator, but match the expected signature from middleware
    log_data = create_base_log_data(event=event,
                                      username=user,
                                      action=action,
                                      target=target,
                                      object_id=object_id,
                                      method=method,
                                      status=status)
    # Middleware currently doesn't pass full user object, so user_id/email might be missing
    # If needed, middleware could fetch user object based on request.user
    return log_data

def match_admin_path(path: str) -> Optional[Dict[str, str]]:
    """
    Matches the request path against predefined admin URL patterns (using constants).
    """
    for pattern, action_constant in ADMIN_URL_PATTERNS:
        match = re.match(pattern, path)
        if match:
            info = {'action_type': action_constant} # Store the constant event name as action_type
            groups = match.groups()
            # Extract groups based on pattern, avoiding magic indices
            if action_constant in [EVENT_ADMIN_EDIT_OBJECT, EVENT_ADMIN_DELETE_OBJECT, EVENT_ADMIN_VIEW_OBJECT_LIST, EVENT_ADMIN_ADD_OBJECT]:
                if len(groups) >= 2:
                    info['app_label'] = groups[0]
                    info['model_name'] = groups[1]
                if len(groups) >= 3 and action_constant in [EVENT_ADMIN_EDIT_OBJECT, EVENT_ADMIN_DELETE_OBJECT]:
                    info['object_id'] = groups[2]
            return info
    return None

def resolve_event_name(action_type: str, method: str) -> str:
    """
    Determines the specific event name based on action type (event constant) and HTTP method.
    """
    if method == 'POST':
        # POST_EVENT_MAP keys are the action_type constants
        return POST_EVENT_MAP.get(action_type, action_type) # Default to action_type if not specific mapping
    elif method == 'GET':
        # GET_EVENT_MAP keys are the action_type constants
        return GET_EVENT_MAP.get(action_type, action_type) # Default to action_type
    else:
        return action_type # Default for other methods

def is_loggable_request(request, response) -> bool:
    """
    Determines if the given request/response should be logged based on predefined rules.

    Args:
        request: The Django HttpRequest object.
        response: The Django HttpResponse object.

    Returns:
        True if the request should be logged, False otherwise.
    """
    path = request.path
    method = request.method
    status_code = response.status_code

    # Rule 1: Must be an admin path
    if not path.startswith('/admin/'):
        return False

    # Rule 2: Skip specific non-essential patterns
    if any(pattern in path for pattern in SKIP_LOGGING_PATTERNS):
        return False

    # Rule 3: Always log POST requests to the login page (handled separately for success/fail)
    # The main middleware logic handles login POST logging explicitly.
    # This function focuses on *other* loggable events.
    # We let the middleware decide *how* to log login attempts.
    # if path.startswith('/admin/login/') and method == 'POST':
    #     return True # Let middleware handle specific login/fail cases

    # Rule 4: Log successful main page GET requests (exclude assets)
    if method == 'GET':
        # Exclude URLs containing dots likely indicating asset files (e.g., .js, .css)
        is_asset = re.search(r'/admin/.*\.', path)
        return not is_asset and status_code == 200

    # Rule 5: Log successful/redirecting POST requests (excluding login, handled above)
    elif method == 'POST':
         # Exclude login POSTs here because they are handled explicitly in middleware __call__
        if path.startswith('/admin/login/'):
             return False
        return status_code in [200, 201, 302] # Successful creation, update, deletion etc.

    # Rule 6: Default to not logging other methods or unsuccessful requests
    return False 

# --- User Activity Log Helpers (Updated to use constants and LogEventType) ---

def log_user_activity(event: str, user: User, **extra_data):
    """Logs a general user activity event using LogEventType.USER_ACTIVITY."""
    if not HAS_LOG_SERVICE:
        return
    log_data = create_base_log_data(event=event, user=user, **extra_data)
    log_event(LogEventType.USER_ACTIVITY, log_data)

def log_dashboard_visit(user: User):
    log_user_activity(EVENT_DASHBOARD_VISIT, user, details='User visited the main dashboard')

def log_profile_update(user: User, changes: Dict):
    log_user_activity(EVENT_PROFILE_UPDATE, user, changes=changes, details='User updated profile info')

def log_account_deleted(user_id: int, username: str, email: str):
    if not HAS_LOG_SERVICE:
        return
    log_data = create_base_log_data(
        event=EVENT_ACCOUNT_DELETED,
        user_id=user_id,
        username=username,
        email=email,
        details='User permanently deleted their account'
    )
    log_data = {k: v for k, v in log_data.items() if v is not None}
    log_event(LogEventType.USER_ACTIVITY, log_data)

def log_user_created(user: User):
    log_user_activity(
        EVENT_USER_CREATED, user,
        first_name=user.first_name,
        last_name=user.last_name,
        details='New user account created'
    )

def log_user_login(user: User, method: str = 'unknown'):
    log_user_activity(EVENT_LOGIN, user, method=method, details=f'User logged in via {method}')

def log_user_logout(user: User, method: str = 'unknown'):
    log_user_activity(EVENT_LOGOUT, user, method=method, details=f'User logged out via {method}')

def log_login_failed(username_or_email: str, reason: str = 'Invalid credentials', method: str = 'unknown'):
    if not HAS_LOG_SERVICE:
        return
    log_data = create_base_log_data(
        event=EVENT_LOGIN_FAILED,
        username=username_or_email,
        method=method,
        reason=reason,
        details=f'Login attempt failed for {username_or_email}'
    )
    # Ensure None values are removed
    log_data = {k: v for k, v in log_data.items() if v is not None}
    log_event(LogEventType.USER_ACTIVITY, log_data) 