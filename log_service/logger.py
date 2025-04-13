import json
import logging
import os
from datetime import datetime
from pathlib import Path

from django.conf import settings

from log_service.events import get_valid_log_types, register_event

# Get valid log types from the events module
VALID_LOG_TYPES = get_valid_log_types()

def log_event(log_type: str, data: dict) -> None:
    """
    Log an event to the appropriate log file in JSON format.
    
    Args:
        log_type: one of the valid log types (see log_service.events)
        data: dictionary containing keys like 'event', 'user_id', 'details', etc.
    
    Returns:
        None
    
    The function will:
    - Auto-create the correct dated folder and log file
    - Append structured JSON logs to the correct file
    - Log errors to a fallback file if a failure occurs
    - Automatically register new event types and events
    """
    # Check if the log_type is valid
    global VALID_LOG_TYPES
    if log_type not in VALID_LOG_TYPES:
        # Auto-register new log types to make the system more flexible
        register_event_type(log_type)
        # Refresh the valid log types
        VALID_LOG_TYPES = get_valid_log_types()
        
    try:
        # Register the specific event if provided
        if 'event' in data:
            register_event(log_type, data['event'])
            
        # Ensure data has a timestamp
        if 'timestamp' not in data:
            data['timestamp'] = datetime.now().isoformat()
        
        # Create log directory path for today
        today = datetime.now().strftime('%Y-%m-%d')
        daily_log_dir = Path(settings.LOGS_DIR) / today
        
        # Ensure the directory exists
        daily_log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create the log file path
        log_file_path = daily_log_dir / f"{log_type}.log"
        
        # Append the log entry as JSON
        with open(log_file_path, 'a') as log_file:
            log_file.write(json.dumps(data) + '\n')
            
    except Exception as e:
        _log_failure(f"Failed to log {log_type} event: {str(e)}", data)

def _log_failure(error_message: str, data: dict = None) -> None:
    """
    Log a failure to the fallback log file.
    
    Args:
        error_message: Description of the error
        data: The data that failed to be logged
        
    Returns:
        None
    """
    try:
        # Ensure the logs directory exists
        Path(settings.LOGS_DIR).mkdir(parents=True, exist_ok=True)
        
        # Create the fallback log file path
        fallback_log_path = Path(settings.LOGS_DIR) / 'failures.log'
        
        # Create a failure entry
        failure_entry = {
            'timestamp': datetime.now().isoformat(),
            'error': error_message,
            'data': data
        }
        
        # Append the failure entry as JSON
        with open(fallback_log_path, 'a') as fallback_file:
            fallback_file.write(json.dumps(failure_entry) + '\n')
            
    except Exception as e:
        # Last resort: use Python's logging
        logging.error(f"Critical failure in logging system: {str(e)}")
        logging.error(f"Original error: {error_message}")
        if data:
            logging.error(f"Original data: {data}")

# Import register_event_type here to avoid circular import
from log_service.events import register_event_type 