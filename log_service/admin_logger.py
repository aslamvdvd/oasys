"""
Admin activity logging module using LogEventType Enum and Constants.

This module provides functions to log admin activities throughout the platform.
"""

from django.utils.encoding import force_str

# Import Enum and Constants
from .events import (
    LogEventType,
    EVENT_ADMIN_ADDED, EVENT_ADMIN_CHANGED, EVENT_ADMIN_DELETED
)
# Import base logger and utils if needed for consistency (optional)
from .logger import log_event
# from .utils import create_base_log_data # Could use this, but current structure is fine

# Constants from django.contrib.admin.models
ADDITION = 1
CHANGE = 2
DELETION = 3

def log_admin_action(user, obj, action_flag, change_message=''):
    """
    Log an admin action to Django admin log and custom log service.
    
    Args:
        user: The user performing the action
        obj: The object being operated on
        action_flag: ADDITION, CHANGE, or DELETION from django.contrib.admin.models
        change_message: Description of the changes made
        
    Returns:
        None
    """
    from django.contrib.admin.models import LogEntry # Local import
    from django.contrib.contenttypes.models import ContentType # Local import
    
    content_type = ContentType.objects.get_for_model(obj.__class__)
    
    # Django LogEntry
    LogEntry.objects.log_action(
        user_id=user.id,
        content_type_id=content_type.id,
        object_id=obj.pk,
        object_repr=force_str(obj),
        action_flag=action_flag,
        change_message=change_message
    )
    
    # Map action flag to our event constants
    event_map = {
        ADDITION: EVENT_ADMIN_ADDED,
        CHANGE: EVENT_ADMIN_CHANGED,
        DELETION: EVENT_ADMIN_DELETED
    }
    event_name = event_map.get(action_flag, 'admin_unknown_action') # Fallback event name
    action_type = event_name # Use the event name itself as the action type here
    
    # Log to custom log_service using Enum
    log_event(LogEventType.ADMIN, {
        'event': event_name,
        # Consider using create_base_log_data if standardizing user fields
        'user_id': user.id,
        'username': user.username,
        'content_type': f"{content_type.app_label}.{content_type.model}",
        'object_id': obj.pk,
        'object_repr': force_str(obj),
        'action': action_type, # Redundant with event, but kept for potential filtering
        'change_message': change_message,
        # Add timestamp automatically by log_event
    })

def log_admin_addition(user, obj, change_message=''):
    """
    Log an admin addition action.
    """
    log_admin_action(user, obj, ADDITION, change_message)

def log_admin_change(user, obj, change_message=''):
    """
    Log an admin change action.
    """
    log_admin_action(user, obj, CHANGE, change_message)

def log_admin_deletion(user, obj, change_message=''):
    """
    Log an admin deletion action.
    """
    log_admin_action(user, obj, DELETION, change_message) 