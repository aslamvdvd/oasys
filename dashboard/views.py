from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import logout
from django.db import transaction
import logging # Import logging

# Import specific log helpers
from log_service.utils import (
    log_dashboard_visit,
    log_profile_update,
    log_account_deleted,
    log_user_logout # General user logout helper
)

logger = logging.getLogger(__name__)

# Create your views here.

@login_required
def home(request):
    """
    Renders the main dashboard homepage.
    Logs the visit event.
    """
    context = {'user': request.user}
    log_dashboard_visit(request.user)
    return render(request, 'dashboard/home.html', context)

@login_required
def profile(request):
    """
    Handles viewing and updating the user profile, and account deletion.
    Logs profile updates and account deletions.
    """
    user = request.user
    
    if request.method == 'POST':
        action = request.POST.get('action', '')
        logger.debug(f"Profile POST action: {action} for user {user.username}")
        
        if action == 'update_profile':
            return _handle_profile_update(request, user)
                
        elif action == 'delete_account':
            return _handle_account_deletion(request, user)
        
        else:
            logger.warning(f"Unknown profile action received: {action}")
            messages.error(request, "Invalid action requested.")

    # GET request or failed POST action
    context = {'user': user}
    return render(request, 'dashboard/profile.html', context)

def _handle_profile_update(request, user):
    """
    Helper function to process profile update form submission.
    """
    # Store old values before update for logging changes
    old_values = {
        'first_name': user.first_name,
        'middle_name': user.middle_name,
        'last_name': user.last_name,
        'bio': user.bio
    }
    
    # Extract new values from POST data
    new_values = {
        'first_name': request.POST.get('first_name', ''),
        'middle_name': request.POST.get('middle_name', ''),
        'last_name': request.POST.get('last_name', ''),
        'bio': request.POST.get('bio', '')
    }

    try:
        with transaction.atomic():
            # Update user object
            user.first_name = new_values['first_name']
            user.middle_name = new_values['middle_name']
            user.last_name = new_values['last_name']
            user.bio = new_values['bio']
            user.save(update_fields=['first_name', 'middle_name', 'last_name', 'bio'])
        
        logger.info(f"User profile updated successfully for {user.username}")
        messages.success(request, "Profile updated successfully!")
        
        # Log the changes
        changes = {key: {'old': old_values[key], 'new': new_values[key]} 
                   for key in old_values if old_values[key] != new_values[key]}
        if changes: # Only log if something actually changed
            log_profile_update(user, changes)
        else:
            logger.info(f"Profile update submitted for {user.username}, but no values changed.")
            
    except Exception as e:
        logger.error(f"Error updating profile for {user.username}: {e}", exc_info=True)
        messages.error(request, "An error occurred while updating your profile.")

    return redirect('dashboard:profile') # Redirect back to profile page

def _handle_account_deletion(request, user):
    """
    Helper function to process account deletion request.
    """
    delete_confirmation = request.POST.get('delete_confirmation', '')
    
    if delete_confirmation.lower() != 'delete':
        logger.warning(f"Account deletion confirmation failed for user {user.username}. Input: '{delete_confirmation}'")
        messages.error(request, "Account deletion failed. Please type 'delete' to confirm.")
        return redirect('dashboard:profile') # Redirect back

    # Store details before deletion
    user_id = user.id
    username = user.username
    email = user.email
    
    try:
        # Log out the user first
        log_user_logout(user, method='account_deletion') # Log logout before session is destroyed
        logout(request)
        
        # Delete the user account within a transaction
        with transaction.atomic():
            user.delete()
        
        logger.info(f"User account deleted successfully: {username} ({user_id})")
        messages.success(request, "Your account has been permanently deleted.")
        
        # Log the deletion event (after successful deletion)
        log_account_deleted(user_id, username, email)
        
        # Redirect to a public page (e.g., welcome page)
        return redirect('core:welcome')
        
    except Exception as e:
        logger.error(f"Error deleting account for {username} ({user_id}): {e}", exc_info=True)
        messages.error(request, "An error occurred during account deletion. Please try again or contact support.")
        # If logout happened but deletion failed, user is logged out.
        # If logout failed, user might still be logged in.
        # Redirecting to profile might be confusing if logged out.
        # Redirecting to welcome page is safer.
        return redirect('core:welcome')

@login_required
def spaces(request):
    """
    Renders the spaces page (placeholder).
    """
    context = {'user': request.user}
    return render(request, 'dashboard/spaces.html', context)
