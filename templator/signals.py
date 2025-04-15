import logging
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.db import transaction
from django.core.exceptions import ValidationError

from .models import Template
from .utils import process_template_upload, cleanup_template_directory, _log_templator_event
from log_service.events import EVENT_TEMPLATE_ERROR

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Template)
def template_post_save(sender, instance, created, **kwargs):
    """
    Signal handler to process the template after it's been saved.
    Validates, extracts, and updates the template instance.
    """
    # Only process if the zip_file field is set
    if not instance.zip_file:
        logger.debug(f"Template {instance.pk} saved without zip file, skipping processing.")
        return

    # Basic check to avoid reprocessing if path already exists and not created
    # More robust checks might involve comparing file hashes if necessary
    if not created and instance.extraction_path:
        logger.debug(f"Template {instance.pk} update, extraction path exists, skipping re-processing.")
        # Potentially add logic here to re-process if zip_file actually changed
        return
    
    logger.info(f"Processing template upload for Template {instance.pk} ({instance.name})...")
    try:
        # Perform the processing within a transaction
        with transaction.atomic():
            extraction_path = process_template_upload(instance)
            
            # Update extraction_path if it changed or was newly set
            if str(extraction_path) != instance.extraction_path:
                logger.info(f"Updating extraction path for Template {instance.pk} to {extraction_path}")
                # Use update() to avoid triggering the post_save signal again
                Template.objects.filter(pk=instance.pk).update(extraction_path=str(extraction_path))
                # Refresh instance in memory if needed elsewhere, though not strictly necessary here
                # instance.refresh_from_db(fields=['extraction_path'])
        logger.info(f"Successfully processed template upload for Template {instance.pk}.")

    except ValidationError as ve:
        # ValidationErrors are expected (e.g., bad zip format) and should have been
        # logged by process_template_upload. We log here for signal context.
        logger.warning(f"Validation error during template_post_save for {instance.pk}: {ve}")
        # Optionally, delete the invalid Template instance or mark it as inactive
        # instance.is_active = False
        # instance.save(update_fields=['is_active'])
        # Or: instance.delete() # Be careful with this
        pass # Let the user see the validation error in the admin/form

    except Exception as e:
        # Catch unexpected errors during processing
        logger.error(f"Unexpected error during template_post_save for {instance.pk}: {e}", exc_info=True)
        # Log using the templator helper as well
        _log_templator_event(EVENT_TEMPLATE_ERROR, instance, 
                             error=f"Unexpected error in post_save signal: {str(e)}")
        # Decide if instance should be marked inactive or deleted on unexpected errors
        pass

@receiver(pre_delete, sender=Template)
def template_pre_delete(sender, instance, **kwargs):
    """
    Signal handler to clean up the template files before deleting the Template instance.
    """
    logger.info(f"Cleaning up directory for Template {instance.pk} before deletion.")
    try:
        cleanup_template_directory(instance)
    except Exception as e:
        # Log cleanup errors but don't prevent deletion
        logger.error(f"Error during template_pre_delete cleanup for {instance.pk}: {e}", exc_info=True)
        _log_templator_event(EVENT_TEMPLATE_ERROR, instance, 
                             error=f"Error during pre_delete cleanup: {str(e)}") 