"""
log_service - A modular, structured logging system for the OASYS platform.

This package provides logging functionality for various system components.
It is not intended to be exposed through URLs or views.
"""

# Make the log_event function directly importable from the package
from .logger import log_event

# Make event management functions directly importable from the package
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

# Removed imports from the deleted admin_logger.py
# from log_service.admin_logger import (
#     log_admin_action,
#     log_admin_addition,
#     log_admin_change,
#     log_admin_deletion
# )

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

__all__ = [
    # Core function
    'log_event',
    # Enums
    'LogEventType',
    'LogSeverity',
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
