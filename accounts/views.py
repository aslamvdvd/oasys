from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView, FormView, View, UpdateView, TemplateView, DeleteView
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView, PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
import logging # Import logging

from log_service.utils import (
    log_user_created,
    log_user_login,
    log_user_logout,
    log_login_failed,
    log_profile_update,
    log_password_change, # Added password change helper
    log_password_reset_request, # Added reset request helper
    log_password_reset_complete, # Added reset complete helper
    log_account_deleted, # Added account deleted helper
    HAS_LOG_SERVICE # Import check
)
from .forms import SignupForm, LoginForm, ProfileUpdateForm
from .models import User
from .backends import EmailOrUsernameBackend

logger = logging.getLogger(__name__)

class SignupView(CreateView):
    """
    Handles user registration using SignupForm.
    Logs user creation and automatically logs the user in.
    """
    template_name = 'core/signup.html'
    form_class = SignupForm
    success_url = reverse_lazy('dashboard:home')

    def form_valid(self, form):
        """
        Called when the signup form is valid. Saves the user, logs them in,
        and logs the creation event.
        """
        response = super().form_valid(form)
        user = self.object # The user created by CreateView
        
        # Log the user in using the custom backend
        login(self.request, user, backend='accounts.backends.EmailOrUsernameBackend')
        messages.success(self.request, "Account created successfully. Welcome to OASYS!")
        
        # Log user creation event using the new signature
        if HAS_LOG_SERVICE:
            source = f'{self.__class__.__name__}.form_valid'
            log_user_created(user=user, request=self.request, source=source)
            
        return response

    def form_invalid(self, form):
        """
        Called when the signup form is invalid.
        """
        logger.warning(f"Signup form invalid: {form.errors.as_json()}")
        messages.error(self.request, "Account creation failed. Please check the errors below.")
        return super().form_invalid(form)

class CustomLoginView(LoginView):
    """
    Handles user login using LoginForm and the custom EmailOrUsernameBackend.
    Logs successful and failed login attempts.
    """
    template_name = 'core/login.html'
    form_class = LoginForm
    redirect_authenticated_user = True # Redirect if already logged in
    authentication_form = LoginForm # Ensure correct form is used
    
    def get(self, request, *args, **kwargs):
        """Clears messages when rendering the login page initially."""
        storage = messages.get_messages(request)
        for _ in storage: pass # Consume messages
        return super().get(request, *args, **kwargs)
    
    def get_success_url(self):
        """Redirects to the dashboard upon successful login."""
        return reverse_lazy('dashboard:home')

    def form_valid(self, form):
        """
        Called for successful login. Logs the event.
        """
        # The user is already logged in by LoginView's default form_valid
        response = super().form_valid(form)
        user = self.request.user
        messages.success(self.request, "Successfully logged in. Welcome back!")
        
        # Log successful login using the new signature
        if HAS_LOG_SERVICE:
            source = f'{self.__class__.__name__}.form_valid'
            log_user_login(user=user, request=self.request, source=source)
            
        return response

    def form_invalid(self, form):
        """
        Called for failed login. Logs the event.
        """
        response = super().form_invalid(form)
        messages.error(self.request, "Login failed. Please check your username/email and password.")
        
        # Log failed login attempt using the new signature
        username_or_email = form.cleaned_data.get('username', '') # 'username' field holds email or username
        if HAS_LOG_SERVICE:
            source = f'{self.__class__.__name__}.form_invalid'
            log_login_failed(
                username_or_email=username_or_email, 
                request=self.request, 
                source=source, 
                reason='Invalid credentials (form validation)'
            )
            
        return response

class CustomLogoutView(View):
    """
    Handles user logout.
    Logs the logout event.
    """
    def get(self, request):
        """Logs out the user and redirects."""
        # Clear messages first
        storage = messages.get_messages(request)
        for _ in storage: pass # Consume messages
        
        user = request.user
        if user.is_authenticated:
            if HAS_LOG_SERVICE:
                source = f'{self.__class__.__name__}.get'
                log_user_logout(user=user, request=request, source=source) 
                
            logout(request)
            messages.success(request, "You have been logged out successfully.")
        else:
            logger.info("Logout view accessed by unauthenticated user.")

        return redirect(reverse_lazy('core:welcome'))

# --- Profile Views --- 

# Use LoginRequiredMixin to ensure user is logged in
class ProfileView(LoginRequiredMixin, TemplateView):
    """Displays the logged-in user's profile information."""
    template_name = 'accounts/profile_detail.html'
    # No specific context needed here, template can access 'user' directly
    # We could add logging for profile view access if desired:
    # def get_context_data(self, **kwargs):
    #     context = super().get_context_data(**kwargs)
    #     if HAS_LOG_SERVICE:
    #         log_user_activity(
    #             event_name='profile_view',
    #             user=self.request.user,
    #             request=self.request,
    #             source=f'{self.__class__.__name__}.get_context_data',
    #             message='User viewed their profile page.'
    #         )
    #     return context

class ProfileEditView(LoginRequiredMixin, UpdateView):
    """Handles editing the logged-in user's profile information."""
    model = User
    form_class = ProfileUpdateForm
    template_name = 'accounts/profile_form.html'
    success_url = reverse_lazy('accounts:profile_view') # Redirect back to profile view

    def get_object(self, queryset=None):
        """Ensure the view edits the currently logged-in user."""
        return self.request.user

    def form_valid(self, form):
        """
        Called when the profile update form is valid. Logs the changes.
        """
        # Store changed data before saving for logging
        changed_data = {field: form.cleaned_data[field] for field in form.changed_data}
        
        response = super().form_valid(form)
        user = self.object
        messages.success(self.request, "Profile updated successfully.")
        
        # Log profile update using the helper
        if HAS_LOG_SERVICE and changed_data:
            source = f'{self.__class__.__name__}.form_valid'
            # Log only the fields that actually changed
            log_profile_update(
                user=user, 
                request=self.request, 
                source=source,
                changes=changed_data # Pass dict of changed fields/values
            )
            
        return response

    def form_invalid(self, form):
        """
        Called when the profile update form is invalid.
        """
        logger.warning(f"Profile update form invalid for user {self.request.user.username}: {form.errors.as_json()}")
        messages.error(self.request, "Profile update failed. Please check the errors below.")
        return super().form_invalid(form)

# --- Password Change View --- 

class CustomPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    """Handles changing the user's password, adding logging."""
    template_name = 'accounts/password_change_form.html'
    success_url = reverse_lazy('accounts:password_change_done')
    # Use Django's built-in PasswordChangeForm by default

    def form_valid(self, form):
        """
        Called when the password change form is valid. Logs the event.
        Updates the user's session hash to prevent logout.
        """
        user = form.save()
        # Update the session hash so the user doesn't get logged out
        update_session_auth_hash(self.request, user)
        messages.success(self.request, _('Your password was changed successfully!'))
        
        # Log password change event
        if HAS_LOG_SERVICE:
            source = f'{self.__class__.__name__}.form_valid'
            log_password_change(user=user, request=self.request, source=source)
            
        return super().form_valid(form)

    def form_invalid(self, form):
        """
        Called when the password change form is invalid.
        """
        logger.warning(f"Password change form invalid for user {self.request.user.username}: {form.errors.as_json()}")
        messages.error(self.request, _('Password change failed. Please check the errors below.'))
        return super().form_invalid(form)

# --- Password Reset Views --- 

class CustomPasswordResetView(PasswordResetView):
    """Handles the password reset request, adding logging."""
    template_name = 'accounts/password_reset_form.html'
    email_template_name = 'accounts/password_reset_email.html'
    subject_template_name = 'accounts/password_reset_subject.txt'
    success_url = reverse_lazy('accounts:password_reset_done')
    # Uses Django's built-in PasswordResetForm by default

    def form_valid(self, form):
        """
        Called when the password reset form (email entry) is valid. Logs the event.
        """
        # Find the user associated with the email to log the request
        # Note: Default PasswordResetForm doesn't expose the user directly
        # We need to fetch the user based on the submitted email
        email = form.cleaned_data.get('email')
        users = list(form.get_users(email)) # Get users associated with the email
        
        # Log the request for each user found (typically just one)
        if HAS_LOG_SERVICE:
            source = f'{self.__class__.__name__}.form_valid'
            for user in users:
                log_password_reset_request(user=user, request=self.request, source=source)
        
        # Let the parent class handle sending the email etc.
        return super().form_valid(form)

    def form_invalid(self, form):
        """
        Called when the password reset form is invalid.
        """
        # Avoid logging detailed errors publicly for password reset
        logger.info(f"Password reset form submission failed validation: {form.errors.as_json()}") 
        messages.error(self.request, _("Password reset request failed. Please check the email address."))
        return super().form_invalid(form)

class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    """Handles the actual password reset after clicking the email link, adding logging."""
    template_name = 'accounts/password_reset_confirm.html'
    success_url = reverse_lazy('accounts:password_reset_complete')
    # Uses Django's built-in SetPasswordForm by default

    def form_valid(self, form):
        """
        Called when the new password form is valid. Logs the event.
        """
        # The user is available via self.user after token validation
        user = self.user
        response = super().form_valid(form) # Saves the new password
        messages.success(self.request, _('Your password has been set successfully!'))
        
        # Log password reset completion
        if HAS_LOG_SERVICE and user:
            source = f'{self.__class__.__name__}.form_valid'
            log_password_reset_complete(user=user, request=self.request, source=source)
            
        return response

    def form_invalid(self, form):
        """
        Called when the new password form is invalid.
        """
        logger.warning(f"Password reset confirmation form invalid: {form.errors.as_json()}") 
        messages.error(self.request, _("Password reset failed. Please check the errors below."))
        return super().form_invalid(form)

# --- Account Deletion View --- 

class AccountDeleteView(LoginRequiredMixin, TemplateView):
    """
    Handles user account deletion.
    GET shows confirmation page, POST performs deletion.
    """
    template_name = 'accounts/account_delete_confirm.html'
    success_url = reverse_lazy('core:welcome') # Redirect to welcome page after deletion
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _("Confirm Account Deletion")
        return context

    def post(self, request, *args, **kwargs):
        """Handles the POST request to delete the user account."""
        user = request.user
        user_id = user.id # Store info before deletion
        username = user.username
        email = user.email

        try:
            # Log user out first
            logout(request)
            
            # Delete the user object
            user.delete()
            
            # Log the deletion event
            if HAS_LOG_SERVICE:
                source = f'{self.__class__.__name__}.post'
                log_account_deleted(user_id=user_id, username=username, email=email, source=source)
                
            messages.success(request, _("Your account has been successfully deleted."))
            logger.info(f"User account deleted: id={user_id}, username={username}") # Standard log for confirmation
            
            return redirect(self.success_url)
            
        except Exception as e:
            logger.error(f"Error deleting account for user {username} (ID: {user_id}): {e}", exc_info=True)
            messages.error(request, _("An error occurred while deleting your account. Please try again or contact support."))
            # Redirect back to profile or a safe page if deletion fails mid-process
            return redirect(reverse_lazy('accounts:profile_view'))
