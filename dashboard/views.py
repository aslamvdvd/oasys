from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# Create your views here.

@login_required
def home(request):
    """
    View for rendering the dashboard homepage.
    This view requires the user to be authenticated.
    """
    # In a real implementation, we'd fetch the user's spaces here
    # For demonstration purposes, we're just rendering the template
    context = {
        'user': request.user,
        # Additional context variables would go here
    }
    return render(request, 'dashboard/home.html', context)

@login_required
def profile(request):
    """
    View for rendering the user profile page.
    This view requires the user to be authenticated.
    """
    context = {
        'user': request.user,
    }
    return render(request, 'dashboard/profile.html', context)

@login_required
def spaces(request):
    """
    View for rendering the spaces page.
    This view requires the user to be authenticated.
    """
    context = {
        'user': request.user,
    }
    return render(request, 'dashboard/spaces.html', context)
