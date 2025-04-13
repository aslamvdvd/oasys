from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView, FormView, View
from django.contrib.auth.views import LoginView, LogoutView
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from log_service import log_event
from .forms import SignupForm, LoginForm
from .models import User
from .backends import EmailOrUsernameBackend

class SignupView(CreateView):
    """
    View for user registration.
    """
    template_name = 'accounts/signup.html'
    form_class = SignupForm
    success_url = reverse_lazy('dashboard:home')

    def form_valid(self, form):
        # This method is called when valid form data has been POSTed.
        # It should return an HttpResponse.
        response = super().form_valid(form)
        
        # Log the user in after successful signup
        email = form.cleaned_data.get('email')
        password = form.cleaned_data.get('password1')
        
        # Use our custom backend
        backend = EmailOrUsernameBackend()
        user = backend.authenticate(self.request, username=email, password=password)
        
        if user is not None:
            # Explicitly specify the backend to use
            login(self.request, user, backend='accounts.backends.EmailOrUsernameBackend')
            messages.success(self.request, "Account created successfully. Welcome to OASYS!")
            
            # Log the user creation and login
            log_event('user_activity', {
                'event': 'user_created',
                'user_id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'details': 'New user account created and logged in'
            })
        
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

class CustomLoginView(LoginView):
    """
    Custom login view using our LoginForm.
    """
    template_name = 'accounts/login.html'
    form_class = LoginForm
    redirect_authenticated_user = True
    
    def get(self, request, *args, **kwargs):
        # Clear any existing messages when first loading the login page
        storage = messages.get_messages(request)
        for msg in storage:
            # This loop will consume all messages
            pass
        
        return super().get(request, *args, **kwargs)
    
    def get_success_url(self):
        return reverse_lazy('dashboard:home')

    def form_valid(self, form):
        # Get the form's result first
        response = super().form_valid(form)
        
        # Add success message after login
        messages.success(self.request, "Successfully logged in. Welcome back!")
        
        # Log the successful login event
        log_event('user_activity', {
            'event': 'login',
            'user_id': self.request.user.id,
            'username': self.request.user.username,
            'email': self.request.user.email,
            'method': 'form_login',
            'details': 'User logged in successfully via login form'
        })
        
        return response

    def form_invalid(self, form):
        response = super().form_invalid(form)
        messages.error(self.request, "Login failed. Please check your credentials.")
        
        # Log the failed login attempt if username/email was provided
        username = form.cleaned_data.get('username', '')
        if username:
            log_event('user_activity', {
                'event': 'login_failed',
                'username_or_email': username,
                'method': 'form_login',
                'reason': 'Invalid credentials',
                'details': 'Login attempt failed with provided username/email'
            })
        
        return response

class CustomLogoutView(View):
    """
    View for logging out users.
    """
    def get(self, request):
        # First clear any existing messages
        storage = messages.get_messages(request)
        for msg in storage:
            # This loop will consume all messages
            pass
        
        if request.user.is_authenticated:
            # Log the logout event before actually logging out
            user_id = request.user.id
            username = request.user.username
            email = request.user.email
            
            logout(request)
            messages.success(request, "You have been logged out successfully.")
            
            # Log the logout event
            log_event('user_activity', {
                'event': 'logout',
                'user_id': user_id,
                'username': username,
                'email': email,
                'method': 'explicit_logout',
                'details': 'User explicitly logged out'
            })
        
        return redirect(reverse_lazy('core:welcome'))
