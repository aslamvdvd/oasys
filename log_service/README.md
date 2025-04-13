# Log Service for OASYS

A modular, structured logging system for the OASYS platform.

## Purpose

This Django app provides structured JSON logging for internal system events across the OASYS platform. It is designed to keep internal logs (not accessible to users) and log important system-level activities.

## Features

- **Directory-based logging**: Logs are organized by date (YYYY-MM-DD folders)
- **JSON formatted logs**: All logs are stored as JSON strings for structured logging
- **Multiple log types**: Supports various log types (user_activity, space_activity, social_media, engine)
- **Dynamic event registration**: Automatically registers new event types and events
- **Error handling**: Fallback logging mechanism for errors during the logging process
- **Log rotation**: Management command to delete old logs
- **Event management**: Tools for listing, adding, and managing event types and events

## Usage

### Basic Logging

```python
from log_service import log_event

# Log a user login event
log_event('user_activity', {
    'event': 'login',
    'user_id': user.id,
    'username': user.username,
    'details': 'Successful login via web interface'
})

# Log a space creation event
log_event('space_activity', {
    'event': 'created',
    'space_id': space.id,
    'owner_id': space.owner.id,
    'space_name': space.name
})
```

### Registering New Event Types

```python
from log_service import register_event_type, register_event

# Register a new event type
register_event_type('api_calls', 'API-related events such as requests and responses')

# Register a new event under an event type
register_event('api_calls', 'api_request')

# Now you can log events with this type
log_event('api_calls', {
    'event': 'api_request',
    'endpoint': '/api/v1/users',
    'method': 'GET',
    'status_code': 200,
    'duration_ms': 45
})
```

### Log Structure

Logs are saved in this directory structure:

```
logs/
├── YYYY-MM-DD/
│   ├── user_activity.log
│   ├── space_activity.log
│   ├── social_media.log
│   ├── engine.log
│   ├── templator.log   <-- Template operations
│   └── admin.log       <-- Admin interface actions
├── failures.log
└── event_registry.json
```

### Event Registry

The system maintains an `event_registry.json` file that stores all registered event types and their events. This ensures that the system "remembers" all event types across restarts.

### Management Commands

#### Rotate Logs

To delete logs older than 30 days:

```bash
python manage.py rotate_logs 30
```

To simulate what would be deleted without actually deleting:

```bash
python manage.py rotate_logs 30 --dry-run
```

#### Manage Events

List all event types and their registered events:

```bash
python manage.py manage_events list
```

List events for a specific event type:

```bash
python manage.py manage_events list --event-type=user_activity
```

Add a new event type:

```bash
python manage.py manage_events add-type api_calls "API-related events such as requests and responses"
```

Add a new event:

```bash
python manage.py manage_events add-event api_calls api_request
```

## Supported Log Types

- `user_activity`: User-related events (login, logout, profile updates, etc.)
- `space_activity`: Space-related events (creation, updates, deletion, etc.)
- `social_media`: Social media integrations and activities
- `engine`: Backend processing and computational activities
- *Any new event type*: The system automatically registers new event types when encountered

## Specialized Log Types

In addition to general logging, the log_service provides specialized logging for specific components:

### Admin Logging

The `admin_logger` module provides specialized logging for admin interface actions:

```python
from log_service import log_admin_addition, log_admin_change, log_admin_deletion

# In your ModelAdmin class:
def save_model(self, request, obj, form, change):
    """Override save_model to log admin actions."""
    super().save_model(request, obj, form, change)
    
    if change:
        log_admin_change(request.user, obj, f"Object {obj} was updated")
    else:
        log_admin_addition(request.user, obj, f"Object {obj} was created")

def delete_model(self, request, obj):
    """Override delete_model to log admin actions."""
    super().delete_model(request, obj)
    log_admin_deletion(request.user, obj, f"Object {obj} was deleted")
```

Admin logs are stored in the `admin.log` file in the date-based directory structure (`logs/YYYY-MM-DD/admin.log`).

### Templator Logging

The templator app has specialized logging in the `templator.log` file in the date-based directory structure.

## Implementation Notes

- Uses environment-configured paths (via settings.LOGS_DIR)
- No URLs or views are exposed
- All logs are written as newline-delimited JSON for easy parsing
- Auto-registration of new event types and events makes the system extensible 