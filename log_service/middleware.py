"""
Middleware for logging administrative actions.
Connects signals for login/logout events and logs general admin activity via middleware.
"""
import logging

from django.contrib.auth import user_logged_out
from django.contrib.auth.signals import user_login_failed
from django.dispatch import receiver
from django.http import HttpRequest, HttpResponse

# Import new logger, event types, severity, and helpers
from .events import LogEventType, LogSeverity
from .logger import log_event
from .utils import (
    log_user_logout, 
    log_login_failed, 
    log_user_login, 
    match_admin_path, 
    resolve_admin_event_name, 
    is_loggable_admin_request,
    log_exception, # <-- Import log_exception
    HAS_LOG_SERVICE # Check if service is active
)

logger = logging.getLogger(__name__) # For middleware internal messages

# --- Signal Receivers --- 

@receiver(user_logged_out)
def handle_admin_logout(sender, request: HttpRequest, user, **kwargs):
    """
    Log user logout specifically from the admin interface using the utility function.
    """
    if not HAS_LOG_SERVICE: return
    
    # Check if it's an admin logout path
    if user and request and request.path.startswith('/admin/logout/'):
        source = f'{__name__}.handle_admin_logout'
        logger.debug(f"Signal received for admin logout: user={user.username}, source={source}")
        # Use the helper from utils
        log_user_logout(user=user, request=request, source=source)

@receiver(user_login_failed)
def handle_admin_login_failure(sender, credentials, request: HttpRequest, **kwargs):
    """
    Log failed login attempts to the admin interface using the utility function.
    """
    if not HAS_LOG_SERVICE: return
    
    if request and request.path.startswith('/admin/login/'):
        username = credentials.get('username', 'unknown')
        source = f'{__name__}.handle_admin_login_failure'
        logger.debug(f"Signal received for admin login failure: user={username}, source={source}")
        # Use the helper from utils
        log_login_failed(
            username_or_email=username, 
            request=request, 
            source=source, 
            reason='Invalid credentials (captured by signal)'
        )

# --- Middleware Class --- 

class AdminActivityMiddleware:
    """
    Middleware to log admin activity using centralized logging functions.
    Handles successful logins and general admin actions.
    Relies on signals for logout and failed login events.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        logger.info(f"AdminActivityMiddleware initialized. Log Service Available: {HAS_LOG_SERVICE}")

    def __call__(self, request: HttpRequest):
        # Execute the request-response cycle first
        response = self.get_response(request)

        # Skip logging if the service is not configured
        if not HAS_LOG_SERVICE:
            return response
            
        try:
            # Handle Successful Login POSTs explicitly
            # Check for specific conditions indicating a successful admin login redirect
            if (
                request.path.startswith('/admin/login/') and 
                request.method == 'POST' and 
                request.user.is_authenticated and 
                response.status_code == 302 # Typically redirects after successful login
            ):
                source = f'{self.__class__.__name__}.__call__' # Use class name
                logger.debug(f"Middleware detected successful admin login: user={request.user.username}")
                log_user_login(user=request.user, request=request, source=source)
                # No need to log failure here, signal handler covers that.
                return response # Login handled, proceed no further with logging this request

            # Handle general loggable requests (excluding login/logout handled elsewhere)
            # Use the utility function to check if this request/response combo should be logged
            if is_loggable_admin_request(request, response) and request.user.is_authenticated:
                admin_info = match_admin_path(request.path)
                if admin_info:
                    self._log_general_admin_action(request, response, admin_info)
            
        except Exception as e:
            # Log any errors occurring within the logging middleware itself
            logger.error(f"Error in AdminActivityMiddleware: {e}", exc_info=True)
            # Optionally, use log_exception if it's safe and available
            # from .utils import log_exception
            # log_exception(request, e, source=f'{self.__class__.__name__}.__call__')
            
        return response

    def _log_general_admin_action(self, request: HttpRequest, response: HttpResponse, admin_info: dict):
        """
        Logs general admin activity (views, edits, adds, deletes) using the core log_event.
        """
        action_type = admin_info['action_type'] # Original matched event constant
        # Determine the final, more specific event name based on method (e.g., add -> created)
        event_name = resolve_admin_event_name(action_type, request.method)

        # Construct target identifier
        app_label = admin_info.get('app_label')
        model_name = admin_info.get('model_name')
        object_id = admin_info.get('object_id')

        if app_label and model_name:
            target = f"{app_label}.{model_name}"
            if object_id:
                target += f":{object_id}"
        else:
            # Handle cases like admin dashboard view
            target = 'admin.dashboard' if action_type == 'admin_view_dashboard' else 'admin.unknown'
            
        # Prepare extra data specific to admin actions
        extra = {
            'action_type': action_type, # Include the original action type
            'app_label': app_label,
            'model_name': model_name,
            'object_id': object_id,
            'response_status': response.status_code
        }
        # Remove None values from extra data
        extra_cleaned = {k: v for k, v in extra.items() if v is not None}

        source = f'{self.__class__.__name__}._log_general_admin_action'
        message = f"Admin action: {event_name} on target: {target}"
        
        logger.debug(f"Logging general admin action: event={event_name}, target={target}, user={request.user.username}")

        # Call the core log_event function directly
        log_event(
            event_type=LogEventType.ADMIN,
            event_name=event_name,
            severity=LogSeverity.INFO, # Most admin actions are informational
            user=request.user,
            request=request,
            source=source,
            message=message,
            target=target,
            extra_data=extra_cleaned
        )

# --- Exception Logging Middleware --- 

class ExceptionLoggingMiddleware:
    """
    Catches unhandled exceptions during request processing and logs them.
    Must be placed appropriately in settings.MIDDLEWARE.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        logger.info(f"ExceptionLoggingMiddleware initialized. Log Service Available: {HAS_LOG_SERVICE}")

    def __call__(self, request: HttpRequest):
        try:
            # Process the request normally
            response = self.get_response(request)
            return response
        except Exception as e:
            # Log the exception if the service is available
            if HAS_LOG_SERVICE:
                source = f'{self.__class__.__name__}.__call__'
                try:
                    logger.debug(f"Logging exception from middleware: {type(e).__name__}")
                    # Call the log_exception helper from utils
                    log_exception(request=request, exc=e, source=source)
                except Exception as log_e:
                    # Avoid crashing if logging itself fails
                    logger.critical(
                        f"CRITICAL: Failed to log exception using log_exception in middleware! "
                        f"Original error: {e}. Logging error: {log_e}",
                        exc_info=True
                    )
            else:
                # If log service unavailable, log to standard logger
                logger.error(
                    f"Unhandled exception occurred, but log service is unavailable: {e}", 
                    exc_info=True
                )
            
            # IMPORTANT: Re-raise the exception so Django's default error handling 
            # (or other middleware) still processes it to show an error page.
            raise

# Note: Signal connections are handled by @receiver decorators.