"""
log_service - A modular, structured logging system for the OASYS platform.

This package provides logging functionality for various system components.
It is not intended to be exposed through URLs or views.
"""

# Make the log_event function directly importable from the package
from log_service.logger import log_event

# Make event management functions directly importable from the package
from log_service.events import (
    register_event_type,
    register_event,
    get_valid_log_types,
    get_all_events,
    get_event_type_description,
    get_registered_events
)

# Make admin logging functions directly importable
from log_service.admin_logger import (
    log_admin_action,
    log_admin_addition,
    log_admin_change,
    log_admin_deletion
)
