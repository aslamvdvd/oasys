from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

User = get_user_model()

class EmailBackend(ModelBackend):
    """
    Custom authentication backend to allow users to log in with their email.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            # Check if the username is an email
            # The username field is used by Django's auth system, but in our form 
            # we're actually passing an email into this field
            user = User.objects.get(Q(email__iexact=username))
            
            # Check the password
            if user.check_password(password):
                return user
            return None
            
        except User.DoesNotExist:
            return None
            
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None 