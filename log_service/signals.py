"""
Signals for the log_service app.

These signals allow other parts of the application to be notified 
when log-related operations occur.
"""

from django.dispatch import Signal

# Signal fired when log service configuration changes
log_service_config_changed = Signal() 