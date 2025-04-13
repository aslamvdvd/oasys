from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.db import transaction

from .models import Template
from .utils import process_template_upload, cleanup_template_directory

@receiver(post_save, sender=Template)
def template_post_save(sender, instance, created, **kwargs):
    """
    Signal handler to process the template after it's been saved.
    
    This will:
    1. Validate the ZIP file
    2. Extract it to the appropriate directory
    3. Update the Template instance with the extraction path
    
    Args:
        sender: The sending model class
        instance: The Template instance being saved
        created: Boolean indicating if this is a new instance
        **kwargs: Additional arguments
    """
    # Only process if this is a new template or the zip_file has changed
    if not instance.zip_file:
        return
        
    # If this is an update and the extraction_path is already set, we don't need to process again
    # unless the zip_file has changed (which we can't easily detect here)
    if not created and instance.extraction_path:
        return
    
    # Process the template upload
    try:
        # Process in a transaction so we can roll back if something fails
        with transaction.atomic():
            extraction_path = process_template_upload(instance)
            
            # Update the extraction_path
            if str(extraction_path) != instance.extraction_path:
                instance.extraction_path = str(extraction_path)
                # Prevent infinite recursion by using update instead of save
                Template.objects.filter(pk=instance.pk).update(extraction_path=str(extraction_path))
    except Exception as e:
        # Log the error (process_template_upload should have already logged it)
        # We don't re-raise the exception here to prevent the admin from crashing
        # The validation error should have been shown to the user before this point
        pass

@receiver(pre_delete, sender=Template)
def template_pre_delete(sender, instance, **kwargs):
    """
    Signal handler to clean up the template files before deleting the Template instance.
    
    Args:
        sender: The sending model class
        instance: The Template instance being deleted
        **kwargs: Additional arguments
    """
    cleanup_template_directory(instance) 