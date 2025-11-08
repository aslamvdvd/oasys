"""
Defines log event types (categories) using LogEventType Enum and specific 
event name constants for structured logging across the OASYS platform.
Manages the persistence of discovered event names via event_registry.json for informational purposes.
"""

import json
import logging
from enum import Enum, unique
from pathlib import Path
from typing import Dict, List, Optional, Set

from django.conf import settings

logger = logging.getLogger(__name__)

# --- Enums for Event Types and Standard Severity Levels ---

@unique
class LogEventType(Enum):
    """Categorizes log events, corresponding to log file names/types."""
    USER_ACTIVITY = 'user_activity' # User actions in main app
    ADMIN = 'admin'                 # Actions within the Django admin interface
    APPLICATION = 'application'       # General application events, errors, lifecycle
    SERVER_ACCESS = 'server_access'     # Web server access logs (e.g., Nginx, Apache)
    SERVER_ERROR = 'server_error'       # Web server error logs
    SYSTEM_AUTH = 'system_auth'         # OS-level authentication logs (e.g., /var/log/auth.log)
    SYSTEM_SYSLOG = 'system_syslog'       # General OS syslog messages
    DATABASE = 'database'             # Database general events/errors
    DATABASE_SLOW_QUERY = 'database_slow_query' # Database slow query events
    FIREWALL = 'firewall'             # Firewall activity (e.g., UFW, iptables)
    TEMPLATOR = 'templator'           # Specific templator app events (legacy?)
    TEMPLATOR_ACTIVITY = 'templator_activity' # General templator activity (legacy?)
    # Consider consolidating TEMPLATOR and TEMPLATOR_ACTIVITY into APPLICATION?

    @classmethod
    def get_description(cls, event_type) -> str:
        descriptions = {
            cls.USER_ACTIVITY: 'User actions (login, logout, profile, etc.)',
            cls.ADMIN: 'Django admin interface activity',
            cls.APPLICATION: 'Application lifecycle, errors, business logic events',
            cls.SERVER_ACCESS: 'Web server access log entries (e.g., Nginx)',
            cls.SERVER_ERROR: 'Web server error log entries (e.g., Nginx)',
            cls.SYSTEM_AUTH: 'OS-level authentication events (/var/log/auth.log)',
            cls.SYSTEM_SYSLOG: 'OS-level system messages (/var/log/syslog)',
            cls.DATABASE: 'Database general operations, errors, statements',
            cls.DATABASE_SLOW_QUERY: 'Database slow query logs',
            cls.FIREWALL: 'Firewall activity logs (e.g., UFW)',
            cls.TEMPLATOR: 'Specific Templator app events',
            cls.TEMPLATOR_ACTIVITY: 'General Templator app activity (legacy)',
        }
        return descriptions.get(event_type, 'Unknown event type')

@unique
class LogSeverity(Enum):
    """Standard log severity levels."""
    DEBUG = 'DEBUG'
    INFO = 'INFO'
    WARNING = 'WARNING'
    ERROR = 'ERROR'
    CRITICAL = 'CRITICAL'

# --- Specific Event Constants (Expand significantly) ---

# Application Events (LogEventType.APPLICATION)
EVENT_APP_START = 'app_start'
EVENT_APP_STOP = 'app_stop'
EVENT_APP_EXCEPTION = 'app_exception'
EVENT_APP_PERMISSION_DENIED = 'permission_denied'
EVENT_APP_TASK_STARTED = 'task_started' # For background tasks
EVENT_APP_TASK_COMPLETED = 'task_completed'
EVENT_APP_TASK_FAILED = 'task_failed'
EVENT_APP_CONFIG_RELOAD = 'config_reload'
EVENT_APP_SENSITIVE_ACTION = 'sensitive_action' # Generic for important actions
EVENT_APP_DATA_EXPORT = 'data_export'
EVENT_APP_DATA_IMPORT = 'data_import'

# User Activity Events (LogEventType.USER_ACTIVITY)
EVENT_LOGIN = 'login'
EVENT_LOGOUT = 'logout'
EVENT_LOGIN_FAILED = 'login_failed'
EVENT_USER_CREATED = 'user_created'
EVENT_PROFILE_UPDATE = 'profile_update'
EVENT_ACCOUNT_DELETED = 'account_deleted'
EVENT_DASHBOARD_VISIT = 'dashboard_visit'
EVENT_PASSWORD_RESET_REQUEST = 'password_reset_request'
EVENT_PASSWORD_RESET_COMPLETE = 'password_reset_complete'
EVENT_PASSWORD_CHANGE = 'password_change'
EVENT_EMAIL_CHANGE_REQUEST = 'email_change_request'
EVENT_EMAIL_CHANGE_COMPLETE = 'email_change_complete'

# Templator Events (LogEventType.TEMPLATOR / TEMPLATOR_ACTIVITY)
EVENT_TEMPLATE_UPLOADED = 'template_uploaded'
EVENT_TEMPLATE_ERROR = 'template_error'
EVENT_TEMPLATE_DELETED = 'template_deleted'

# Admin Events (LogEventType.ADMIN)
EVENT_ADMIN_LOGIN = 'admin_login'
EVENT_ADMIN_LOGOUT = 'admin_logout'
EVENT_ADMIN_LOGIN_FAILED = 'admin_login_failed'
EVENT_ADMIN_LOGIN_PAGE = 'admin_login_page' # GET request
EVENT_ADMIN_VIEW_DASHBOARD = 'admin_view_dashboard'
EVENT_ADMIN_VIEW_OBJECT_LIST = 'admin_view_object_list'
EVENT_ADMIN_EDIT_OBJECT = 'admin_edit_object' # GET/POST distinction via log data
EVENT_ADMIN_ADD_OBJECT = 'admin_add_object'   # GET/POST distinction via log data
EVENT_ADMIN_DELETE_OBJECT = 'admin_delete_object' # GET/POST distinction via log data
EVENT_ADMIN_OTHER = 'admin_other' # Catch-all for non-patterned admin views
# Events triggered by admin actions but logged with more detail
EVENT_OBJECT_CREATED = 'object_created' # From admin save
EVENT_OBJECT_UPDATED = 'object_updated' # From admin save
EVENT_OBJECT_DELETED = 'object_deleted' # From admin delete

# Server Access Events (LogEventType.SERVER_ACCESS) - Parsed from external logs
EVENT_HTTP_REQUEST = 'http_request' 

# Server Error Events (LogEventType.SERVER_ERROR) - Parsed from external logs
EVENT_SERVER_ERROR_ENTRY = 'server_error_entry'

# System Auth Events (LogEventType.SYSTEM_AUTH) - Parsed from external logs
EVENT_AUTH_SUCCESS = 'auth_success'
EVENT_AUTH_FAILURE = 'auth_failure'
EVENT_AUTH_SESSION_OPEN = 'auth_session_open'
EVENT_AUTH_SESSION_CLOSE = 'auth_session_close'

# System Syslog Events (LogEventType.SYSTEM_SYSLOG) - Parsed from external logs
EVENT_SYSLOG_ENTRY = 'syslog_entry'

# Database Events
EVENT_DB_ERROR = 'db_error'               # (LogEventType.DATABASE)
EVENT_DB_QUERY = 'db_query'               # (LogEventType.DATABASE) - If logging all statements
EVENT_DB_SLOW_QUERY = 'db_slow_query'       # (LogEventType.DATABASE_SLOW_QUERY)

# Firewall Events (LogEventType.FIREWALL) - Parsed from external logs
EVENT_FW_PACKET_ALLOWED = 'fw_packet_allowed'
EVENT_FW_PACKET_DENIED = 'fw_packet_denied'

# --- Event Registry (Stores discovered events per type) ---

_event_registry: Dict[LogEventType, Set[str]] = {e_type: set() for e_type in LogEventType}
_registry_loaded = False

def get_registry_file_path() -> Path:
    """Gets the platform-specific path to the event registry JSON file."""
    log_dir = getattr(settings, 'LOGS_DIR', None)
    if not log_dir:
        raise ValueError("LOGS_DIR setting is not configured.")
    return Path(log_dir) / 'event_registry.json'

def _load_event_registry() -> None:
    """Loads known events from the registry file into the in-memory store (_event_registry)."""
    global _registry_loaded
    if _registry_loaded:
        return

    try:
        registry_path = get_registry_file_path()
        if registry_path.exists():
            logger.debug(f"Loading event registry from: {registry_path}")
            with open(registry_path, 'r') as f:
                registry_data = json.load(f)
            for type_str, events_list in registry_data.items():
                try:
                    event_type_enum = LogEventType(type_str)
                    _event_registry[event_type_enum].update(set(events_list))
                except ValueError:
                    logger.warning(f"Skipping unknown event type '{type_str}' found in registry.")
        else:
             logger.debug("Event registry file not found, starting fresh.")
    except (ValueError, json.JSONDecodeError, IOError, Exception) as e:
        logger.error(f"Failed to load event registry: {e}", exc_info=True)
    finally:
        _registry_loaded = True # Mark as loaded even if failed

def _save_event_registry() -> None:
    """Saves the current in-memory event registry (_event_registry) to its JSON file."""
    if not _registry_loaded: # Avoid saving if loading failed badly initially
        logger.warning("Skipping save of event registry as it wasn't loaded properly.")
        return
        
    try:
        registry_path = get_registry_file_path()
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        serializable_registry = {e_type.value: sorted(list(events)) # Save sorted lists
                                 for e_type, events in _event_registry.items()}
        with open(registry_path, 'w') as f:
            json.dump(serializable_registry, f, indent=2, sort_keys=True)
        logger.debug(f"Event registry saved to: {registry_path}")
    except (ValueError, IOError, Exception) as e:
        logger.error(f"Failed to save event registry: {e}", exc_info=True)

def register_event(event_type: LogEventType, event_name: str) -> None:
    """
    Registers a specific event name string under a LogEventType Enum.
    Ensures the registry is loaded and saves changes if the event is new.
    """
    if not isinstance(event_type, LogEventType):
        logger.error(f"Invalid event_type provided to register_event: {type(event_type)}")
        return # Fail silently for internal use
        
    if not isinstance(event_name, str) or not event_name:
        logger.error(f"Invalid event_name provided to register_event: '{event_name}'")
        return
        
    _load_event_registry() 
    
    # Use setdefault for cleaner add
    event_set = _event_registry.setdefault(event_type, set())
    if event_name not in event_set:
        event_set.add(event_name)
        logger.info(f"Registered new event: Type={event_type.value}, Name='{event_name}'")
        _save_event_registry()

def is_event_registered(event_type: LogEventType, event_name: str) -> bool:
    """Checks if a specific event name string is registered under the given LogEventType."""
    _load_event_registry()
    return event_name in _event_registry.get(event_type, set())

def get_registered_events(event_type: LogEventType) -> Set[str]:
    """Gets all registered event names for a specific LogEventType."""
    _load_event_registry()
    return _event_registry.get(event_type, set()).copy()

# --- Public Info Functions ---

def get_valid_log_types() -> List[str]:
    """Get a list of all valid log type *string values* from the Enum."""
    return [e_type.value for e_type in LogEventType]

def get_event_type_description(event_type_enum: LogEventType) -> Optional[str]:
    """Get the description for a LogEventType Enum member."""
    if isinstance(event_type_enum, LogEventType):
        return LogEventType.get_description(event_type_enum)
    logger.warning(f"Invalid type provided to get_event_type_description: {type(event_type_enum)}")
    return None

def get_all_event_info() -> Dict[str, Dict]:
    """
    Get all event types (as strings) with descriptions and registered events.
    Mainly for inspection or management commands.
    """
    _load_event_registry()
    return {e_type.value: {
                'description': LogEventType.get_description(e_type),
                'registered_events': sorted(list(events))
            } 
            for e_type, events in _event_registry.items()}

# Initialize by loading the registry on module import
_load_event_registry() 