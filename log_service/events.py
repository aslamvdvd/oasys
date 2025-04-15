"""
Event types management using Enums for better structure and type safety.

This module defines and manages event types used throughout the OASYS platform.
It provides functionality to:
1. Store event types and their descriptions
2. Register new event types automatically
3. Provide validation for log_event function
"""

import json
import logging
from enum import Enum, unique
from pathlib import Path
from typing import Dict, List, Optional, Set
from django.conf import settings

logger = logging.getLogger(__name__)

# --- Enums for Event Types and Events ---

@unique
class LogEventType(Enum):
    """Categorizes log events (corresponds to log file names)."""
    USER_ACTIVITY = 'user_activity'
    SPACE_ACTIVITY = 'space_activity'
    SOCIAL_MEDIA = 'social_media'
    ENGINE = 'engine'
    TEMPLATOR = 'templator'
    ADMIN = 'admin'
    TEMPLATOR_ACTIVITY = 'templator_activity' # Kept for backward compatibility

    @classmethod
    def get_description(cls, event_type) -> str:
        """Returns a description for the event type."""
        descriptions = {
            cls.USER_ACTIVITY: 'User-related events (login, logout, profile, etc.)',
            cls.SPACE_ACTIVITY: 'Space-related events (creation, updates, deletion, sharing)',
            cls.SOCIAL_MEDIA: 'Social media integration events',
            cls.ENGINE: 'Backend processing and computational events',
            cls.TEMPLATOR: 'Template management events (uploads, extractions, deletions)',
            cls.ADMIN: 'Admin interface activity logging',
            cls.TEMPLATOR_ACTIVITY: 'General templator app activity (legacy)',
        }
        return descriptions.get(event_type, 'Unknown event type')

# Define specific events as string constants or potentially nested Enums if needed
# Using constants for now simplifies usage with existing string-based logic
# User Activity Events
EVENT_LOGIN = 'login'
EVENT_LOGOUT = 'logout'
EVENT_LOGIN_FAILED = 'login_failed'
EVENT_USER_CREATED = 'user_created'
EVENT_PROFILE_UPDATE = 'profile_update'
EVENT_ACCOUNT_DELETED = 'account_deleted'
EVENT_DASHBOARD_VISIT = 'dashboard_visit'

# Templator Events
EVENT_TEMPLATE_UPLOADED = 'template_uploaded'
EVENT_TEMPLATE_ERROR = 'template_error'
EVENT_TEMPLATE_DELETED = 'template_deleted'

# Admin Events
EVENT_ADMIN_ADDED = 'admin_added'
EVENT_ADMIN_CHANGED = 'admin_changed'
EVENT_ADMIN_DELETED = 'admin_deleted'
EVENT_ADMIN_ACCESS = 'admin_access'
EVENT_ADMIN_LOGIN = 'admin_login'
EVENT_ADMIN_LOGOUT = 'admin_logout'
EVENT_ADMIN_LOGIN_FAILED = 'admin_login_failed'
EVENT_ADMIN_LOGIN_PAGE = 'admin_login_page'
EVENT_ADMIN_VIEW_DASHBOARD = 'admin_view_dashboard'
EVENT_ADMIN_VIEW_OBJECT_LIST = 'admin_view_object_list'
EVENT_ADMIN_EDIT_OBJECT = 'admin_edit_object'
EVENT_ADMIN_DELETE_OBJECT = 'admin_delete_object'
EVENT_ADMIN_ADD_OBJECT = 'admin_add_object'
EVENT_ADMIN_OTHER = 'admin_other'
EVENT_OBJECT_CREATED = 'object_created'
EVENT_OBJECT_UPDATED = 'object_updated'
EVENT_OBJECT_DELETED = 'object_deleted'

# --- Event Registry (Simplified) ---

# In-memory store for registered events per type
# Format: {LogEventType: Set[str]}
_event_registry: Dict[LogEventType, Set[str]] = {e_type: set() for e_type in LogEventType}
_registry_loaded = False

def get_registry_file_path() -> Path:
    """Get the path to the event registry JSON file."""
    return Path(settings.LOGS_DIR) / 'event_registry.json'

def _load_event_registry() -> None:
    """Loads known events from the registry file into the in-memory store."""
    global _registry_loaded
    if _registry_loaded:
        return

    registry_path = get_registry_file_path()
    if registry_path.exists():
        try:
            with open(registry_path, 'r') as f:
                registry_data = json.load(f)
            
            for type_str, events_list in registry_data.items():
                try:
                    event_type_enum = LogEventType(type_str)
                    _event_registry[event_type_enum].update(set(events_list))
                except ValueError:
                    logger.warning(f"Skipping unknown event type '{type_str}' found in registry.")
        except (json.JSONDecodeError, IOError, Exception) as e:
            logger.error(f"Failed to load event registry '{registry_path}': {e}")
    _registry_loaded = True

def _save_event_registry() -> None:
    """Saves the current in-memory event registry to the JSON file."""
    registry_path = get_registry_file_path()
    try:
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        # Convert Enum keys to strings and sets to lists for JSON
        serializable_registry = {e_type.value: list(events) 
                                 for e_type, events in _event_registry.items()}
        with open(registry_path, 'w') as f:
            json.dump(serializable_registry, f, indent=2)
    except IOError as e:
        logger.error(f"Failed to save event registry to '{registry_path}': {e}")

def register_event(event_type: LogEventType, event_name: str) -> None:
    """
    Registers a specific event under an event type Enum.
    Ensures the registry is loaded and saves changes.
    
    Args:
        event_type: The LogEventType Enum member.
        event_name: The specific event name string.
    """
    if not isinstance(event_type, LogEventType):
        raise TypeError("event_type must be a LogEventType Enum member")
        
    _load_event_registry() # Ensure registry is loaded before modifying
    
    if event_name not in _event_registry.get(event_type, set()):
        _event_registry.setdefault(event_type, set()).add(event_name)
        _save_event_registry()

def is_event_valid(event_type: LogEventType, event_name: str) -> bool:
    """
    Checks if a specific event name is registered under the given event type.
    Useful for validation before logging.
    """
    _load_event_registry()
    return event_name in _event_registry.get(event_type, set())

def get_registered_events(event_type: LogEventType) -> Set[str]:
    """
    Gets all registered event names for a specific LogEventType.
    """
    _load_event_registry()
    return _event_registry.get(event_type, set()).copy() # Return a copy

# Initialize by loading the registry on module import
_load_event_registry()

def register_event_type(event_type_str: str, description: str = None) -> None:
    """
    DEPRECATED/Internal use only.
    Ensures an event type exists in the registry primarily for loading.
    Prefer using LogEventType Enum directly.
    """
    try:
        event_type = LogEventType(event_type_str)
        if event_type not in _event_registry:
             _event_registry[event_type] = set()
             # No save needed here usually, as it's for ensuring presence during load/validation
    except ValueError:
        logger.error(f"Attempted to register invalid event type string: {event_type_str}")

def get_valid_log_types() -> List[str]:
    """
    Get a list of all valid log type *string values* from the Enum.
    """
    return [e_type.value for e_type in LogEventType]

def get_event_type_description(event_type_enum: LogEventType) -> Optional[str]:
    """
    Get the description for a LogEventType Enum member.
    """
    if isinstance(event_type_enum, LogEventType):
        return LogEventType.get_description(event_type_enum)
    logger.warning(f"Invalid type provided to get_event_type_description: {type(event_type_enum)}")
    return None

def get_all_events() -> Dict[str, Dict]:
    """
    Get all event types (as strings) and their registered events.
    Mainly for inspection or external use.
    """
    _load_event_registry()
    return {e_type.value: {
                'description': LogEventType.get_description(e_type),
                'registered_events': list(events)
            } 
            for e_type, events in _event_registry.items()} 