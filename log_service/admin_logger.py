"""
Admin activity logging module for the OASYS platform.

This module provides functions to log admin activities throughout the platform.
"""

from django.utils.encoding import force_str
from log_service import log_event

# Constants from django.contrib.admin.models, to avoid circular imports
ADDITION = 1
CHANGE = 2
DELETION = 3

def log_admin_action(user, obj, action_flag, change_message=''):
    """
    Log an admin action to admin.log.
    
    Args:
        user: The user performing the action
        obj: The object being operated on
        action_flag: ADDITION, CHANGE, or DELETION from django.contrib.admin.models
        change_message: Description of the changes made
        
    Returns:
        None
    """
    # Import here to avoid circular imports during app initialization
    from django.contrib.admin.models import LogEntry
    from django.contrib.contenttypes.models import ContentType
    
    # Get the content type for the object
    content_type = ContentType.objects.get_for_model(obj.__class__)
    
    # Create a log entry in LogEntry model
    LogEntry.objects.log_action(
        user_id=user.id,
        content_type_id=content_type.id,
        object_id=obj.pk,
        object_repr=force_str(obj),
        action_flag=action_flag,
        change_message=change_message
    )
    
    # Log the action to admin.log using log_service
    action_types = {
        ADDITION: 'added',
        CHANGE: 'changed',
        DELETION: 'deleted'
    }
    
    action_type = action_types.get(action_flag, 'unknown')
    
    log_event('admin', {
        'event': f'admin_{action_type}',
        'user_id': user.id,
        'username': user.username,
        'content_type': f"{content_type.app_label}.{content_type.model}",
        'object_id': obj.pk,
        'object_repr': force_str(obj),
        'change_message': change_message
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