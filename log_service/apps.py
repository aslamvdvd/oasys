from django.apps import AppConfig


class LogServiceConfig(AppConfig):
    """
    Configuration for the log_service app.
    
    This app provides structured JSON logging for internal system events
    across the OASYS platform. It does not provide any user-facing functionality.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'log_service'
    verbose_name = 'OASYS Logging Service'
