from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import logout
from django.db import transaction

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
    View for rendering the user profile page and handling profile updates.
    This view requires the user to be authenticated.
    """
    user = request.user
    
    if request.method == 'POST':
        action = request.POST.get('action', '')
        print(f"POST request received with action: {action}")
        
        if action == 'update_profile':
            # Handle profile update
            print("Processing profile update")
            with transaction.atomic():
                user.first_name = request.POST.get('first_name', '')
                user.middle_name = request.POST.get('middle_name', '')
                user.last_name = request.POST.get('last_name', '')
                user.bio = request.POST.get('bio', '')
                
                print(f"Updating user profile: {user.first_name} {user.middle_name} {user.last_name}")
                user.save()
                print("User profile saved successfully")
                
                messages.success(request, "Profile updated successfully!")
                return redirect('dashboard:profile')
                
        elif action == 'delete_account':
            # Handle account deletion
            print("Processing account deletion")
            delete_confirmation = request.POST.get('delete_confirmation', '')
            
            if delete_confirmation.lower() == 'delete':
                # Get the user ID before deletion for logging purposes
                user_id = user.id
                user_email = user.email
                print(f"Deleting user {user_id} ({user_email})")
                
                # Log the user out first
                logout(request)
                
                # Permanently delete the user account
                with transaction.atomic():
                    user.delete()  # This will delete the user and all related data with CASCADE
                
                # Add a success message
                messages.success(request, "Your account has been permanently deleted.")
                
                # Redirect to the welcome page
                return redirect('core:welcome')
            else:
                print(f"Delete confirmation failed: '{delete_confirmation}'")
                messages.error(request, "Account deletion failed. Please type 'delete' to confirm.")
    
    context = {
        'user': user,
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
