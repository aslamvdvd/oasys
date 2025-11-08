from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

class UserManager(BaseUserManager):
    """
    Custom user manager for the User model.
    """
    def create_user(self, email, username, first_name, last_name, password=None, **extra_fields):
        """
        Create and save a regular user with the given email, username and password.
        """
        if not email:
            raise ValueError(_('The Email field must be set'))
        if not username:
            raise ValueError(_('The Username field must be set'))
        if not first_name:
            raise ValueError(_('The First name field must be set'))
        if not last_name:
            raise ValueError(_('The Last name field must be set'))
     
        
        email = self.normalize_email(email)
        user = self.model(
            email=email, 
            username=username, 
            first_name=first_name, 
            last_name=last_name, 
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, first_name, last_name, password=None, **extra_fields):
        """
        Create and save a superuser with the given email, username and password.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        
        return self.create_user(email, username, first_name, last_name, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model that uses email as the unique identifier instead of username.
    """
    email = models.EmailField(_('email address'), unique=True)
    username = models.CharField(_('username'), max_length=150, unique=True)
    first_name = models.CharField(_('first name'), max_length=150)
    middle_name = models.CharField(_('middle name'), max_length=150, blank=True)
    last_name = models.CharField(_('last name'), max_length=150)
    bio = models.TextField(_('biography'), blank=True)
    is_staff = models.BooleanField(
        _('staff status'),
        default=False,
        help_text=_('Designates whether the user can log into this admin site.'),
    )
    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_(
            'Designates whether this user should be treated as active. '
            'Unselect this instead of deleting accounts.'
        ),
    )
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')

    def __str__(self):
        return self.email

    def get_full_name(self):
        """
        Return the first_name plus the middle_name plus the last_name, with a space in between.
        """
        if self.middle_name:
            full_name = f"{self.first_name} {self.middle_name} {self.last_name}"
        else:
            full_name = f"{self.first_name} {self.last_name}"
        return full_name.strip()

    def get_short_name(self):
        """Return the short name for the user."""
        return self.first_name
