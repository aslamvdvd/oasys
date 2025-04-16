from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
import logging

from log_service.utils import (
    log_dashboard_visit,
    log_user_activity,
    HAS_LOG_SERVICE
)

logger = logging.getLogger(__name__)

# Create your views here.

@login_required
def home(request):
    """
    Renders the main user dashboard homepage.
    Logs the visit.
    """
    context = {'user': request.user}
    if HAS_LOG_SERVICE:
        source = f'{__name__}.home'
        log_dashboard_visit(user=request.user, request=request, source=source)
        
    return render(request, 'dashboard/home.html', context)

@login_required
def spaces(request):
    """
    Renders the user spaces page (placeholder/future functionality).
    Logs the visit.
    """
    context = {'user': request.user}
    if HAS_LOG_SERVICE:
        source = f'{__name__}.spaces'
        log_user_activity(
            event_name='spaces_view',
            user=request.user,
            request=request,
            source=source,
            message='User viewed the spaces page.'
        )
        
    logger.debug(f"Rendering spaces page for user {request.user.username}")
    return render(request, 'dashboard/spaces.html', context)
