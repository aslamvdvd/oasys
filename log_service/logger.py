import json
import logging
import os
from datetime import datetime
from pathlib import Path

from django.conf import settings

# Import Enum and validation function
from log_service.events import LogEventType, register_event # Removed unused is_event_valid

logger = logging.getLogger(__name__) # Standard logger for internal issues

def log_event(log_type: LogEventType, data: dict) -> None:
    """
    Logs an event to the appropriate log file in JSON format.
    
    This is the core logging function. It ensures the event type is valid,
    registers the specific event name if new, creates necessary directories,
    and appends the JSON log data to the correct file.
    
    Args:
        log_type: The LogEventType Enum member indicating the log category/file.
        data: Dictionary containing event details. The 'event' key (str) is
              highly recommended for specifying the specific action.
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
            # register_event handles existence check internally
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
            json_string = json.dumps(data, default=str) 
            log_file.write(json_string + '\n')
            
    except TypeError as json_err:
        err_msg = f"Failed to serialize log data for {log_type.value}: {json_err}"
        logger.error(err_msg)
        _log_failure(err_msg, {"original_data_keys": list(data.keys())}) 
    except IOError as io_err:
        err_msg = f"Failed to write log file '{log_file_path}': {io_err}"
        logger.error(err_msg)
        _log_failure(err_msg, data)
    except Exception as e:
        err_msg = f"Unexpected error logging {log_type.value} event: {e}"
        logger.exception(err_msg) 
        _log_failure(err_msg, data)

def _log_failure(error_message: str, data: dict = None) -> None:
    """
    Internal helper to log a failure to the fallback `failures.log` file.
    Attempts to safely serialize the original data that caused the failure.
    """
    try:
        log_dir = Path(settings.LOGS_DIR)
        log_dir.mkdir(parents=True, exist_ok=True)
        fallback_log_path = log_dir / 'failures.log'
        serializable_data = None
        if data:
            try:
                json.dumps(data) # Test serialization
                serializable_data = data
            except TypeError:
                try:
                    serializable_data = json.loads(json.dumps(data, default=str))
                except Exception:
                    serializable_data = {"unserializable_data_keys": list(data.keys()), "msg": "Original data could not be serialized"}
            except Exception:
                 serializable_data = {"unserializable_data_keys": list(data.keys()), "msg": "Original data could not be serialized (non-TypeError)"}
                 
        failure_entry = {
            'timestamp': datetime.now().isoformat(),
            'error': error_message,
            'original_data': serializable_data
        }
        
        with open(fallback_log_path, 'a') as fallback_file:
            fallback_file.write(json.dumps(failure_entry, default=str) + '\n') # Add default=str here too
            
    except Exception as e:
        logging.critical(f"CRITICAL FAILURE IN LOGGING SYSTEM: {e}", exc_info=True)
        logging.critical(f"Original Error: {error_message}")
        if data:
            logging.critical(f"Original Data (might be partial/unserializable): {str(data)[:1000]}...")

# No need for late import of register_event_type anymore
# from log_service.events import register_event_type 