from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import logout
from django.db import transaction
import logging

from log_service.utils import (
    log_dashboard_visit,
    log_profile_update,
    log_account_deleted,
    log_user_logout
)

logger = logging.getLogger(__name__)

# Create your views here.

@login_required
def home(request):
    """
    Renders the main user dashboard homepage.
    
    Context:
        user: The authenticated user object.
    
    Logs:
        - `dashboard_visit` upon successful rendering.
    """
    context = {'user': request.user}
    log_dashboard_visit(request.user)
    logger.debug(f"Rendering dashboard home for user {request.user.username}")
    return render(request, 'dashboard/home.html', context)

@login_required
def profile(request):
    """
    Handles viewing the user profile page (GET) and processing profile updates
    or account deletion requests (POST).
    
    Requires the user to be logged in.
    
    Context (GET):
        user: The authenticated user object.
        
    Logs:
        - `profile_update` on successful profile update.
        - `account_deleted` on successful account deletion.
    """
    user = request.user
    
    if request.method == 'POST':
        action = request.POST.get('action', '')
        logger.debug(f"Profile POST action: '{action}' for user {user.username}")
        
        if action == 'update_profile':
            return _handle_profile_update(request, user)
                
        elif action == 'delete_account':
            return _handle_account_deletion(request, user)
        
        else:
            # Handle unknown or missing action
            logger.warning(f"Unknown profile POST action received: '{action}' from user {user.username}")
            messages.error(request, "Invalid action requested.")
            # Fall through to render profile page again

    # GET request or if POST action was invalid
    logger.debug(f"Rendering profile page for user {user.username}")
    context = {'user': user}
    return render(request, 'dashboard/profile.html', context)

def _handle_profile_update(request, user):
    """
    Helper function to process profile update form submission.
    Performs atomic update, logs changes, and redirects.
    """
    old_values = {
        'first_name': user.first_name,
        'middle_name': user.middle_name,
        'last_name': user.last_name,
        'bio': user.bio
    }
    new_values = {
        'first_name': request.POST.get('first_name', ''),
        'middle_name': request.POST.get('middle_name', ''),
        'last_name': request.POST.get('last_name', ''),
        'bio': request.POST.get('bio', '')
    }

    try:
        # Check if any values actually changed
        if old_values == new_values:
             logger.info(f"Profile update submitted for {user.username}, but no values changed.")
             messages.info(request, "No changes detected in profile.")
             return redirect('dashboard:profile')
             
        with transaction.atomic():
            user.first_name = new_values['first_name']
            user.middle_name = new_values['middle_name']
            user.last_name = new_values['last_name']
            user.bio = new_values['bio']
            # Only save fields that might have changed
            user.save(update_fields=['first_name', 'middle_name', 'last_name', 'bio'])
        
        logger.info(f"User profile updated successfully for {user.username}")
        messages.success(request, "Profile updated successfully!")
        
        # Calculate and log the actual changes
        changes = {key: {'old': old_values[key], 'new': new_values[key]} for key in old_values}
        log_profile_update(user, changes)
            
    except Exception as e:
        logger.error(f"Error updating profile for {user.username}: {e}", exc_info=True)
        messages.error(request, "An error occurred while updating your profile. Please try again.")

    return redirect('dashboard:profile')

def _handle_account_deletion(request, user):
    """
    Helper function to process account deletion request.
    Requires explicit confirmation, logs user out, deletes account atomically,
    logs deletion, and redirects.
    """
    delete_confirmation = request.POST.get('delete_confirmation', '')
    
    if delete_confirmation.lower() != 'delete':
        logger.warning(f"Account deletion confirmation failed for user {user.username}. Input: '{delete_confirmation}'")
        messages.error(request, "Account deletion failed. Please type 'delete' exactly to confirm.")
        return redirect('dashboard:profile')

    user_id = user.id
    username = user.username
    email = user.email
    
    try:
        logger.warning(f"Attempting account deletion for user {username} ({user_id})")
        # Log the logout action *before* calling logout()
        log_user_logout(user, method='account_deletion') 
        logout(request) # Destroy session
        logger.info(f"User {username} logged out prior to account deletion.")
        
        with transaction.atomic():
            user.delete()
        
        logger.info(f"User account deleted successfully: {username} ({user_id})")
        messages.success(request, "Your account has been permanently deleted.")
        
        # Log the deletion event *after* successful deletion
        log_account_deleted(user_id, username, email)
        
        return redirect('core:welcome')
        
    except Exception as e:
        # Catch potential errors during logout or delete
        logger.error(f"Error during account deletion process for {username} ({user_id}): {e}", exc_info=True)
        # User might be logged out or not depending on where the error occurred.
        messages.error(request, "An error occurred during account deletion. Your account may or may not have been deleted. Please contact support.")
        # Redirect to a safe public page
        return redirect('core:welcome')

@login_required
def spaces(request):
    """
    Renders the user spaces page (placeholder/future functionality).
    
    Context:
        user: The authenticated user object.
    """
    context = {'user': request.user}
    logger.debug(f"Rendering spaces page for user {request.user.username}")
    return render(request, 'dashboard/spaces.html', context)
