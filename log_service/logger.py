"""
Core logging function (`log_event`) for writing structured JSON logs to date-based directories.

Responsibilities:
- Takes log data (event_type, event_name, user, request, etc.).
- Determines the correct log file based on event_type.
- Creates the log directory structure (LOGS_DIR/YYYY-MM-DD/).
- Formats the log entry as a JSON string.
- Appends the JSON log entry to the appropriate log file.
- Handles failures gracefully, logging them to a separate failures.log.
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from django.conf import settings
from django.http import HttpRequest

# Import enums directly - no models import here
from .choices import EventType, LogLevel
from .events import LogEventType, LogSeverity

# Standard Python logger for internal errors WITHIN the logging service
logger = logging.getLogger(__name__)

# --- Core Log Writing Function ---

def log_event(
    event_type: EventType,
    level: LogLevel = LogLevel.INFO,
    user: settings.AUTH_USER_MODEL = None,
    source: str = None,
    details: str = None,
    request: HttpRequest = None,
    related_object=None,
    # Added new standard fields from LogEvent structure
    event_name: str = None, # Specific event name (e.g., 'user_login')
    severity: LogSeverity = LogSeverity.INFO, # Standardized severity
    message: str = None, # Standardized message field (replaces 'details'?)
    target: str = None, # Optional target identifier
    extra_data: dict = None # Structured extra data
) -> None:
    """
    Core function to create a SystemLog entry.
    Handles potential errors during logging itself.
    Now includes standardized fields like event_name, severity, message, target.
    """
    # --- Moved Import --- 
    from django.contrib.contenttypes.models import ContentType
    from .models import SystemLog  # Import model here to avoid circular imports
    from .utils import HAS_LOG_SERVICE # <-- Import HAS_LOG_SERVICE here
    # --- End Moved Import ---

    if not HAS_LOG_SERVICE:
        # Log to standard logger if service is off but function called?
        # logger.debug("Log service unavailable, log_event call suppressed.")
        return # Do nothing if the service is disabled

    try:
        # Prioritize new standardized fields
        final_details = message if message is not None else details
        final_source = source or 'Unknown'
        final_level = severity.name if severity else level.name # Use severity if provided
        final_event_name = event_name or event_type.name # Use specific name or fallback to type name

        log_entry = SystemLog(
            event_type=event_type.value, # Keep original enum value for DB
            log_level=final_level,     # Store severity/level name
            user=user,
            source=final_source,
            details=final_details or '', # Ensure details/message is stored
            ip_address=_get_client_ip(request) if request else None,
            user_agent=request.META.get('HTTP_USER_AGENT', '') if request else None,
            # New fields
            event_name=final_event_name,
            target=target,
            extra_data=extra_data or {},
        )

        # Handle generic relation for related_object
        if related_object:
            log_entry.content_type = ContentType.objects.get_for_model(related_object)
            log_entry.object_id = related_object.pk

        log_entry.save()

    except Exception as e:
        # Use standard Python logger as a fallback if DB logging fails
        logger.error(f"Failed to create SystemLog entry: {e}", exc_info=True)

# --- Helper Functions ---

def _create_log_entry(
    event_type: LogEventType,
    event_name: str,
    user: Optional[Any], # Keep type hint general
    request: Optional[HttpRequest],
    severity: LogSeverity,
    source: Optional[str],
    message: Optional[str],
    target: Optional[str],
    extra_data: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """Constructs the dictionary representing the log entry."""
    # Import get_user_model inside the function
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    log_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z'),
        "event_type": event_type.value,
        "event_name": event_name,
        "severity": severity.value,
        "source": source,
        "actor": None, 
        "ip_address": None,
        "message": message,
        "target": target,
        "extra_data": extra_data if extra_data else {},
    }

    # Add actor information if user is provided and is the correct type
    if user and isinstance(user, User) and getattr(user, 'is_authenticated', False):
        log_data["actor"] = {
            "username": user.get_username(), # Use get_username() method
            "user_id": user.pk,
            "is_staff": getattr(user, 'is_staff', False),
            "is_superuser": getattr(user, 'is_superuser', False),
        }
    elif user: 
        # Basic representation for other user-like objects or unauthenticated users
        username = getattr(user, 'username', str(user)) # Try to get username, fallback to str()
        log_data["actor"] = {"username": username}
        
    # Add request-specific information if available
    if request and isinstance(request, HttpRequest):
        log_data["ip_address"] = _get_client_ip(request)
        log_data["extra_data"].update({
            "http_method": request.method,
            "http_path": request.path,
            "http_user_agent": request.META.get('HTTP_USER_AGENT'),
            "http_referer": request.META.get('HTTP_REFERER')
        })
        log_data["extra_data"] = {k: v for k, v in log_data["extra_data"].items() if v is not None}
        
    log_data = {k: v for k, v in log_data.items() if v is not None}
    return log_data

def _get_log_file_path(timestamp_str: str, event_type: LogEventType) -> Path:
    """Determines the full path to the log file based on date and event type."""
    log_dir_base = getattr(settings, 'LOGS_DIR', None)
    if not log_dir_base:
        raise ValueError("LOGS_DIR setting is not configured.")
        
    try:
        # Extract date from ISO timestamp
        log_date = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00')).strftime('%Y-%m-%d')
    except ValueError:
        # Fallback if timestamp parsing fails (should not happen with isoformat)
        log_date = datetime.utcnow().strftime('%Y-%m-%d')
        logger.warning(f"Could not parse timestamp '{timestamp_str}' for log directory, using current date.")
        
    log_file_name = f"{event_type.value}.log"
    return Path(log_dir_base) / log_date / log_file_name

def _get_client_ip(request: HttpRequest) -> Optional[str]:
    """Extracts the client IP address from the request, considering proxies."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # Take the first IP in the list if multiple are present
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def _log_failure(
    original_event_type: LogEventType, 
    original_event_name: str, 
    exception: Exception, 
    context: Dict[str, Any]
) -> None:
    """
    Logs details about a failure during the logging process itself.
    Writes to a dedicated failures.log file in the root LOGS_DIR.
    Avoids calling log_event to prevent recursion on failure.
    """
    try:
        log_dir_base = getattr(settings, 'LOGS_DIR', None)
        if not log_dir_base:
            # Cannot log failure if LOGS_DIR is not set
            print(f"CRITICAL: LOGS_DIR not set. Failed to log failure: {exception}") # Use print as last resort
            return
            
        failure_log_path = Path(log_dir_base) / 'failures.log'
        failure_log_path.parent.mkdir(parents=True, exist_ok=True)

        failure_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z'),
            "severity": LogSeverity.CRITICAL.value,
            "source": "log_service.logger._log_failure",
            "message": f"Failed to log event '{original_event_name}' ({original_event_type.value})",
            "error_type": type(exception).__name__,
            "error_message": str(exception),
            "original_context": {
                # Be selective about what context to log to avoid huge logs/sensitive data
                'event_type': original_event_type.value,
                'event_name': original_event_name,
                'user': str(context.get('user')), # Avoid logging full user object
                'request_path': context.get('request').path if context.get('request') else None,
                'severity': context.get('severity').value if context.get('severity') else None,
                'source': context.get('source'),
                'target': context.get('target')
            }
        }

        log_line = json.dumps(failure_data, default=str) + '\n'
        with open(failure_log_path, 'a') as f:
            f.write(log_line)
            
    except Exception as inner_e:
        # Ultimate fallback if logging the failure itself fails
        print(f"CRITICAL: Failed to write to failures.log. Original error: {exception}. Inner error: {inner_e}")

# No need for late import of register_event_type anymore
# from log_service.events import register_event_type 