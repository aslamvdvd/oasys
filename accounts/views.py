from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView, FormView, View
from django.contrib.auth.views import LoginView, LogoutView
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
import logging # Import logging

from log_service import log_event
from log_service.utils import (
    log_user_created,
    log_user_login,
    log_user_logout,
    log_login_failed
)
from .forms import SignupForm, LoginForm
from .models import User
from .backends import EmailOrUsernameBackend

logger = logging.getLogger(__name__)

class SignupView(CreateView):
    """
    Handles user registration using SignupForm.
    Logs user creation and automatically logs the user in.
    """
    template_name = 'accounts/signup.html'
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
        logger.info(f"New user created and logged in: {user.username}")
        
        # Log user creation event
        log_user_created(user)
        # Log the implicit login after signup
        log_user_login(user, method='signup')
        
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
    template_name = 'accounts/login.html'
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
        logger.info(f"User logged in successfully: {user.username}")
        
        # Log successful login
        log_user_login(user, method='form_login')
        
        return response

    def form_invalid(self, form):
        """
        Called for failed login. Logs the event.
        """
        response = super().form_invalid(form)
        messages.error(self.request, "Login failed. Please check your username/email and password.")
        
        # Log failed login attempt
        username_or_email = form.cleaned_data.get('username', '') # 'username' field holds email or username
        logger.warning(f"Login failed for identifier: {username_or_email}")
        log_login_failed(username_or_email, method='form_login')
        
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
            logger.info(f"Logging out user: {user.username}")
            # Log before session is destroyed
            log_user_logout(user, method='explicit_logout') 
            logout(request)
            messages.success(request, "You have been logged out successfully.")
        else:
            logger.info("Logout view accessed by unauthenticated user.")
        
        return redirect(reverse_lazy('core:welcome'))
