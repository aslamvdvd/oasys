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

# Import HAS_LOG_SERVICE
from .utils import HAS_LOG_SERVICE
from .events import LogEventType, register_event, LogSeverity # Import LogSeverity

# Standard Python logger for internal errors WITHIN the logging service
logger = logging.getLogger(__name__)

# --- Core Log Writing Function ---

def log_event(
    event_type: LogEventType,
    event_name: str,
    user: Optional[Any] = None, # Keep type hint general or use settings.AUTH_USER_MODEL later if needed
    request: Optional[HttpRequest] = None,
    severity: LogSeverity = LogSeverity.INFO,
    source: Optional[str] = None,
    message: Optional[str] = None,
    target: Optional[str] = None,
    extra_data: Optional[Dict[str, Any]] = None
) -> None:
    """
    Logs a structured event to the appropriate log file based on event_type.

    Args:
        event_type: The category of the event (e.g., LogEventType.USER_ACTIVITY).
        event_name: A specific name for the event (e.g., events.EVENT_LOGIN).
        user: The User object associated with the event, if any.
        request: The Django HttpRequest object, if available, to extract IP, method, etc.
        severity: The severity level of the log (LogSeverity Enum).
        source: The origin of the log event (e.g., 'app.views.profile', 'middleware', 'parser.nginx').
        message: A human-readable message describing the event.
        target: The object or resource the action was performed on, if applicable.
        extra_data: A dictionary of additional context-specific data (must be JSON-serializable).
                      **IMPORTANT**: Ensure no sensitive data (passwords, raw POST, tokens) is included here.
    """
    if not HAS_LOG_SERVICE:
        logger.debug("Log service not configured (LOGS_DIR missing). Skipping log_event.")
        return
        
    try:
        # 1. Register the event name if not seen before (for discovery/management)
        register_event(event_type, event_name)

        # 2. Prepare Log Data Structure
        log_entry = _create_log_entry(
            event_type, event_name, user, request, severity, source, message, target, extra_data
        )

        # 3. Determine Log File Path
        log_file_path = _get_log_file_path(log_entry['timestamp'], event_type)
        # Define today_dir based on the file path
        today_dir = log_file_path.parent

        # 4. Ensure Directory Exists
        try:
            today_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.error(f"Failed to create log directory {today_dir}: {e}", exc_info=True)
            # Pass arguments matching _log_failure definition
            _log_failure(event_type, event_name, e, locals())
            return # Cannot proceed if directory fails

        # 5. Write to Log File with error handling
        try:
            # Use default=str to handle potential non-serializable types like datetime
            log_line = json.dumps(log_entry, default=str)
            with open(log_file_path, 'a', encoding='utf-8') as f:
                f.write(log_line + '\n')
        except (IOError, OSError) as e:
            logger.error(f"Failed to write to log file {log_file_path}: {e}", exc_info=True)
            # Pass arguments matching _log_failure definition
            _log_failure(event_type, event_name, e, locals()) # Log the original data + error
        except TypeError as e: # Handle JSON serialization errors
            logger.error(f"JSON serialization error for log event: {e}. Attempting to log minimal info.", exc_info=True)
            # Pass arguments matching _log_failure definition
            _log_failure(event_type, event_name, e, locals())

    except Exception as e:
        # Catch-all for unexpected errors during log preparation
        logger.critical(f"Unexpected critical error during log_event processing: {e}", exc_info=True)
        try:
            # Attempt to log the failure itself
            _log_failure(event_type, event_name, e, locals())
        except Exception as log_fail_e:
            logger.critical(f"Failed to write to failures.log: {log_fail_e}", exc_info=True)

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