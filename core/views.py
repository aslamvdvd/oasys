import logging
from django.shortcuts import render

# Import log helper if available
try:
    from log_service.utils import log_user_activity, EVENT_DASHBOARD_VISIT # Reusing dashboard visit for now
    HAS_LOG_SERVICE = True
except ImportError:
    HAS_LOG_SERVICE = False
    logger = logging.getLogger(__name__)
    def log_user_activity(event, user, **kwargs): logger.warning("Log service unavailable.")

logger = logging.getLogger(__name__) # Standard logger

# Create your views here.

def welcome(request):
    """
    Renders the static welcome/landing page.
    
    Logs a visit event if the user is authenticated and log service is available.
    """
    context = {}
    
    # Log visit only if user is logged in (anonymous visits might be too noisy)
    if HAS_LOG_SERVICE and request.user.is_authenticated:
        try:
            # Using EVENT_DASHBOARD_VISIT temporarily, consider adding EVENT_WELCOME_VISIT
            log_user_activity(EVENT_DASHBOARD_VISIT, request.user, details="User visited welcome page")
        except Exception as e:
            logger.error(f"Failed to log welcome page visit for {request.user.username}: {e}", exc_info=True)
            
    return render(request, 'core/welcome.html', context)
