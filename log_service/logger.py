import json
import logging
import os
from datetime import datetime
from pathlib import Path

from django.conf import settings

# Import Enum and validation function
from log_service.events import LogEventType, is_event_valid, register_event

logger = logging.getLogger(__name__) # Standard logger for internal issues

def log_event(log_type: LogEventType, data: dict) -> None:
    """
    Log an event to the appropriate log file in JSON format using LogEventType Enum.
    
    Args:
        log_type: The LogEventType Enum member indicating the log category/file.
        data: Dictionary containing event details ('event' key is highly recommended).
    
    Returns:
        None
    
    The function will:
    - Validate the log_type against the Enum.
    - Validate the specific 'event' string if present and register if new.
    - Auto-create the correct dated folder and log file.
    - Append structured JSON logs to the correct file.
    - Log errors to a fallback file if a failure occurs.
    """
    # Validate log_type is a valid Enum member
    if not isinstance(log_type, LogEventType):
        err_msg = f"Invalid log_type provided. Expected LogEventType Enum, got {type(log_type)}."
        logger.error(err_msg)
        _log_failure(err_msg, data)
        return
        
    try:
        event_name = data.get('event')
        # Auto-register the specific event if it's provided and new
        if event_name:
            # No need to check is_event_valid first, register handles existence check
            register_event(log_type, event_name)
            
        # Ensure data has a timestamp if not provided
        data.setdefault('timestamp', datetime.now().isoformat())
        
        # Create log directory path for today
        today = datetime.now().strftime('%Y-%m-%d')
        daily_log_dir = Path(settings.LOGS_DIR) / today
        
        # Ensure the directory exists
        daily_log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create the log file path using the Enum value
        log_file_path = daily_log_dir / f"{log_type.value}.log"
        
        # Append the log entry as JSON
        with open(log_file_path, 'a') as log_file:
            # Ensure all data is serializable
            json_string = json.dumps(data, default=str) # Use default=str for non-serializable types
            log_file.write(json_string + '\n')
            
    except TypeError as json_err:
        err_msg = f"Failed to serialize log data for {log_type.value}: {json_err}"
        logger.error(err_msg)
        _log_failure(err_msg, {"original_data_keys": list(data.keys())}) # Log keys only to avoid unserializable data
    except IOError as io_err:
        err_msg = f"Failed to write log file '{log_file_path}': {io_err}"
        logger.error(err_msg)
        _log_failure(err_msg, data)
    except Exception as e:
        # Catch any other unexpected errors
        err_msg = f"Unexpected error logging {log_type.value} event: {e}"
        logger.exception(err_msg) # Log full traceback for unexpected errors
        _log_failure(err_msg, data)

def _log_failure(error_message: str, data: dict = None) -> None:
    """
    Log a failure to the fallback log file.
    Ensures data logged here is JSON serializable.
    """
    try:
        # Ensure the logs directory exists
        log_dir = Path(settings.LOGS_DIR)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        fallback_log_path = log_dir / 'failures.log'
        
        # Ensure data is serializable, fallback to string representation
        serializable_data = None
        if data:
            try:
                json.dumps(data) # Test serialization
                serializable_data = data
            except TypeError:
                 # If original data fails, try converting problematic items to strings
                serializable_data = json.loads(json.dumps(data, default=str))
            except Exception:
                 # Ultimate fallback: just log keys or a simple message
                 serializable_data = {"unserializable_data_keys": list(data.keys()), "msg": "Original data could not be serialized"}
                 
        failure_entry = {
            'timestamp': datetime.now().isoformat(),
            'error': error_message,
            'original_data': serializable_data
        }
        
        with open(fallback_log_path, 'a') as fallback_file:
            fallback_file.write(json.dumps(failure_entry) + '\n')
            
    except Exception as e:
        # Last resort: use Python's standard logging
        logging.critical(f"CRITICAL FAILURE IN LOGGING SYSTEM: {e}", exc_info=True)
        logging.critical(f"Original Error: {error_message}")
        if data:
            logging.critical(f"Original Data (might be partial/unserializable): {str(data)[:1000]}...")

# No need for late import of register_event_type anymore
# from log_service.events import register_event_type 