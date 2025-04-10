from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView, FormView, View
from django.contrib.auth.views import LoginView, LogoutView
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from .forms import SignupForm, LoginForm
from .models import User
from .backends import EmailBackend

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
        backend = EmailBackend()
        user = backend.authenticate(self.request, username=email, password=password)
        
        if user is not None:
            login(self.request, user)
            messages.success(self.request, _("Account created successfully. Welcome to OASYS!"))
        
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
        
        return response

    def form_invalid(self, form):
        response = super().form_invalid(form)
        messages.error(self.request, "Login failed. Please check your credentials.")
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
            logout(request)
            messages.success(request, "You have been logged out successfully.")
        
        return redirect(reverse_lazy('core:welcome'))
