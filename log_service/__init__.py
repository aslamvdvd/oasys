"""
log_service - A modular, structured logging system for the OASYS platform.

This package provides logging functionality for various system components.
It is not intended to be exposed through URLs or views.
"""

# Import event management functions first to avoid circular imports
from .events import (
    LogEventType,
    LogSeverity,
    register_event,
    is_event_registered,
    get_registered_events,
    get_valid_log_types,
    get_event_type_description,
    get_all_event_info
)

# Import choices
from .choices import EventType, LogLevel

# Make key components easily accessible (optional, but common practice)
from .utils import (
    log_exception,
    log_permission_denied,
    log_sensitive_action,
    log_user_activity,
    log_dashboard_visit,
    log_profile_update,
    log_account_deleted,
    log_user_created,
    log_user_login,
    log_user_logout,
    log_login_failed,
    log_password_reset_request,
    log_password_reset_complete,
    log_password_change,
    log_email_change_request,
    log_email_change_complete
    # Admin helpers are usually used only by middleware, might not need exposure here
)

# Import log_event after all other imports to avoid circular dependencies
from .logger import log_event

__all__ = [
    # Core function
    'log_event',
    # Enums
    'LogEventType',
    'LogSeverity',
    'EventType',
    'LogLevel',
    # Event registry functions
    'register_event', 
    'is_event_registered',
    'get_registered_events',
    'get_valid_log_types',
    'get_event_type_description',
    'get_all_event_info',
    # Utility helpers
    'log_exception',
    'log_permission_denied',
    'log_sensitive_action',
    'log_user_activity',
    'log_dashboard_visit',
    'log_profile_update',
    'log_account_deleted',
    'log_user_created',
    'log_user_login',
    'log_user_logout',
    'log_login_failed',
    'log_password_reset_request',
    'log_password_reset_complete',
    'log_password_change',
    'log_email_change_request',
    'log_email_change_complete'
]
