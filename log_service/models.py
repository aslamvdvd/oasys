from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

# Create your models here.
class SystemLog(models.Model):
    """
    Stores system logs in the database for quick querying through Django admin and API.
    """
    timestamp = models.DateTimeField(auto_now_add=True)
    event_type = models.CharField(max_length=50)  # Using the EventType enum value
    event_name = models.CharField(max_length=100, null=True, blank=True)  # Specific event name
    log_level = models.CharField(max_length=20)  # Using the LogLevel enum value
    source = models.CharField(max_length=255, null=True, blank=True)  # Component/module that generated the log
    details = models.TextField(null=True, blank=True)  # The message (old field name)
    
    # User who performed the action (if available)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='system_logs'
    )
    
    # Generic foreign key to any model
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    related_object = GenericForeignKey('content_type', 'object_id')
    
    # Request-specific data
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    
    # Additional fields
    target = models.CharField(max_length=255, null=True, blank=True)  # Optional target identifier
    extra_data = models.JSONField(default=dict, blank=True)  # Additional structured data
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['event_type']),
            models.Index(fields=['log_level']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['user']),
        ]
    
    def __str__(self):
        return f"{self.timestamp} - {self.event_type} - {self.log_level} - {self.details[:50]}"
