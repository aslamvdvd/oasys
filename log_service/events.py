"""
Event types management for the log_service app.

This module defines and manages event types used throughout the OASYS platform.
It provides functionality to:
1. Store event types and their descriptions
2. Register new event types automatically
3. Provide validation for log_event function
"""

from typing import Dict, List, Optional, Set
import json
from pathlib import Path
from django.conf import settings

# Dictionary to store event types and their descriptions
# Format: {event_type: {'description': str, 'registered_events': set()}}
EVENT_TYPES = {
    'user_activity': {
        'description': 'User-related events such as login, logout, registration, profile updates',
        'registered_events': {
            'login', 'logout', 'user_created', 'profile_update', 'account_deleted',
            'login_failed', 'dashboard_visit'
        }
    },
    'space_activity': {
        'description': 'Space-related events such as creation, updates, deletion, sharing',
        'registered_events': set()
    },
    'social_media': {
        'description': 'Social media integration-related events like sharing, posting, connections',
        'registered_events': set()
    },
    'engine': {
        'description': 'Backend processing and computational events',
        'registered_events': set()
    },
    'templator': {
        'description': 'Template management events such as uploads, extractions, and deletions',
        'registered_events': {
            'template_uploaded', 'template_error', 'template_deleted'
        }
    },
    'admin': {
        'description': 'Admin interface activity logging',
        'registered_events': {
            'admin_added', 'admin_changed', 'admin_deleted', 'admin_access'
        }
    },
    'templator_activity': {
        'description': 'General templator app activity (duplicate of templator for backward compatibility)',
        'registered_events': {
            'template_uploaded', 'template_error', 'template_deleted'
        }
    }
}

# Path to the event registry file
def get_registry_file_path() -> Path:
    """Get the path to the event registry JSON file."""
    return Path(settings.LOGS_DIR) / 'event_registry.json'

def load_event_registry() -> None:
    """
    Load previously registered event types and events from the event registry file.
    If the file doesn't exist, it will be created when register_event is called.
    """
    registry_path = get_registry_file_path()
    if registry_path.exists():
        try:
            with open(registry_path, 'r') as f:
                registry_data = json.load(f)
                
            # Update the EVENT_TYPES with data from the registry
            for event_type, data in registry_data.items():
                if event_type not in EVENT_TYPES:
                    EVENT_TYPES[event_type] = {
                        'description': data.get('description', f'Automatically registered {event_type}'),
                        'registered_events': set(data.get('registered_events', []))
                    }
                else:
                    # Merge registered events
                    EVENT_TYPES[event_type]['registered_events'].update(
                        set(data.get('registered_events', []))
                    )
        except Exception as e:
            # Log the error but continue with default event types
            import logging
            logging.error(f"Failed to load event registry: {str(e)}")

def save_event_registry() -> None:
    """
    Save the current event registry to a JSON file.
    This preserves the event types and their registered events across application restarts.
    """
    registry_path = get_registry_file_path()
    
    # Ensure the directory exists
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert the EVENT_TYPES dict to a serializable format
    serializable_registry = {}
    for event_type, data in EVENT_TYPES.items():
        serializable_registry[event_type] = {
            'description': data['description'],
            'registered_events': list(data['registered_events'])
        }
    
    try:
        with open(registry_path, 'w') as f:
            json.dump(serializable_registry, f, indent=2)
    except Exception as e:
        import logging
        logging.error(f"Failed to save event registry: {str(e)}")

def register_event_type(event_type: str, description: str = None) -> None:
    """
    Register a new event type if it doesn't exist.
    
    Args:
        event_type: The type of event (e.g., 'user_activity', 'api_calls')
        description: Optional description of the event type
        
    Returns:
        None
    """
    if event_type not in EVENT_TYPES:
        EVENT_TYPES[event_type] = {
            'description': description or f'Automatically registered {event_type}',
            'registered_events': set()
        }
        save_event_registry()

def register_event(event_type: str, event_name: str) -> None:
    """
    Register a specific event under an event type.
    If the event type doesn't exist, it will be created automatically.
    
    Args:
        event_type: The type of event (e.g., 'user_activity')
        event_name: The specific event name (e.g., 'login', 'profile_update')
        
    Returns:
        None
    """
    # If the event type doesn't exist, create it
    if event_type not in EVENT_TYPES:
        register_event_type(event_type)
    
    # Add the event to the registered events
    EVENT_TYPES[event_type]['registered_events'].add(event_name)
    save_event_registry()

def get_valid_log_types() -> List[str]:
    """
    Get a list of all valid log types.
    
    Returns:
        List of valid log type strings
    """
    return list(EVENT_TYPES.keys())

def get_event_type_description(event_type: str) -> Optional[str]:
    """
    Get the description for an event type.
    
    Args:
        event_type: The type of event
        
    Returns:
        Description string if found, None otherwise
    """
    if event_type in EVENT_TYPES:
        return EVENT_TYPES[event_type]['description']
    return None

def get_registered_events(event_type: str) -> Set[str]:
    """
    Get all registered events for a specific event type.
    
    Args:
        event_type: The type of event
        
    Returns:
        Set of registered event names
    """
    if event_type in EVENT_TYPES:
        return EVENT_TYPES[event_type]['registered_events']
    return set()

def get_all_events() -> Dict[str, Dict]:
    """
    Get all event types and their registered events.
    
    Returns:
        Dictionary of event types with descriptions and registered events
    """
    return EVENT_TYPES

# Initialize by loading the event registry
load_event_registry() 