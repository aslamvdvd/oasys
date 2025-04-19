import logging
from pathlib import Path # Import Path
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.db import transaction
from django.core.exceptions import ValidationError

from .models import Template
from .utils import process_template_upload, cleanup_template_directory, _log_templator_event
from log_service.events import EVENT_TEMPLATE_ERROR, EVENT_TEMPLATE_UPLOADED # Added upload event

# Import analyzer components
try:
    from analyzer.validator import validate_template
    from analyzer.constants import STATUS_SUCCESS, STATUS_ERROR, Framework
    HAS_ANALYZER = True
except ImportError:
    HAS_ANALYZER = False
    # Define dummy function if analyzer is not available
    def validate_template(path, info): 
        logger.warning("Analyzer app not found or validate_template not available.")
        return { "status": "skipped", "framework": Framework.UNKNOWN.value, "errors": [], "warnings": ["Analyzer unavailable"] }
    # Dummy constants
    STATUS_SUCCESS = "success"
    STATUS_ERROR = "error"
    class Framework: UNKNOWN = type('obj', (object,), {'value': 'unknown'})

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Template)
def template_post_save(sender, instance, created, **kwargs):
    """
    Signal handler to process the template after it's been saved.
    Validates, extracts, runs analyzer, and updates the template instance.
    """
    # Only process if the zip_file field is set
    if not instance.zip_file:
        logger.debug(f"Template {instance.pk} saved without zip file, skipping processing.")
        return

    # Avoid reprocessing if path already exists and not a new instance
    # More robust checks might involve comparing file hashes if necessary
    # Or check if zip_file field was updated specifically
    if not created and instance.extraction_path:
        # Check if zip_file was part of the update
        update_fields = kwargs.get('update_fields', None)
        if update_fields is None or 'zip_file' not in update_fields:
             logger.debug(f"Template {instance.pk} update, extraction path exists and zip_file not changed, skipping re-processing.")
             return
        else:
             logger.info(f"Template {instance.pk} updated with a new zip_file, reprocessing...")
    
    logger.info(f"Processing template upload for Template {instance.pk} ({instance.name})...")
    extraction_path_str = None
    analysis_results = None
    
    try:
        # Perform the processing within a transaction
        with transaction.atomic():
            # 1. Extract the template zip file
            extraction_path = process_template_upload(instance)
            extraction_path_str = str(extraction_path)
            logger.info(f"Template {instance.pk} extracted to: {extraction_path_str}")
            
            # Update extraction_path field immediately to avoid recursion if analyzer fails later
            if extraction_path_str != instance.extraction_path:
                logger.info(f"Updating extraction path for Template {instance.pk} to {extraction_path_str}")
                Template.objects.filter(pk=instance.pk).update(extraction_path=extraction_path_str)
                instance.extraction_path = extraction_path_str # Update instance in memory
                
            # 2. Run the analyzer if available
            if HAS_ANALYZER and extraction_path:
                logger.info(f"Running analyzer on extracted path: {extraction_path}")
                # Prepare template info for the analyzer
                template_info = {
                    'name': instance.name,
                    'slug': instance.slug,
                    'category_slug': instance.category.slug if instance.category else 'uncategorized',
                    'author_username': instance.uploaded_by.username if instance.uploaded_by else 'unknown',
                    'version': '1.0' # TODO: Add version field to Template model?
                    # 'framework': instance.framework # Pass existing framework if model has it
                }
                analysis_results = validate_template(extraction_path, template_info)
                logger.info(f"Analyzer finished for Template {instance.pk} with status: {analysis_results.get('status')}")
                
                # Handle analysis results
                detected_framework = analysis_results.get('framework', Framework.UNKNOWN.value)
                
                # Update detected_framework on the model
                if detected_framework != instance.detected_framework:
                    Template.objects.filter(pk=instance.pk).update(detected_framework=detected_framework)
                    instance.detected_framework = detected_framework # Update instance in memory
                    
                # Log warnings/errors from analyzer
                for warning in analysis_results.get('warnings', []):
                    logger.warning(f"Analyzer Warning (Template {instance.pk}): {warning}")
                    _log_templator_event(EVENT_TEMPLATE_ERROR, instance, error=f"Analyzer Warning: {warning}")
                    
                if analysis_results.get('status') == STATUS_ERROR:
                    error_list = analysis_results.get('errors', ["Unknown analyzer error"])
                    error_msg = "Analyzer failed: " + '; '.join(error_list)
                    logger.error(f"Analyzer Error (Template {instance.pk}): {error_msg}")
                    _log_templator_event(EVENT_TEMPLATE_ERROR, instance, error=error_msg)
                    # Mark as inactive or raise error to show in admin?
                    # For now, log it and potentially leave it active but with errors logged
                    # Template.objects.filter(pk=instance.pk).update(is_active=False)
                    # raise ValidationError(f"Template analysis failed: {error_msg}") # This will prevent saving in admin
                else:
                     _log_templator_event(EVENT_TEMPLATE_UPLOADED, instance, framework=detected_framework) # Log success
            else:
                 _log_templator_event(EVENT_TEMPLATE_UPLOADED, instance, framework="unknown (analyzer unavailable)") # Log success without analysis
                 
        logger.info(f"Successfully processed signals for Template {instance.pk}.")

    except ValidationError as ve:
        logger.warning(f"Validation error during template processing for {instance.pk}: {ve}")
        _log_templator_event(EVENT_TEMPLATE_ERROR, instance, error=f"Validation Error: {ve}")
        # If extraction failed, cleanup potentially partially extracted files
        if extraction_path_str:
             logger.warning(f"Cleaning up potentially failed extraction at: {extraction_path_str}")
             cleanup_template_directory(Path(extraction_path_str)) # Use Path object
             Template.objects.filter(pk=instance.pk).update(extraction_path="") # Clear path
        # Reraise to show error in admin
        # raise ve # Commented out to allow saving even if validation fails initially

    except Exception as e:
        logger.error(f"Unexpected error during template processing for {instance.pk}: {e}", exc_info=True)
        _log_templator_event(EVENT_TEMPLATE_ERROR, instance, 
                             error=f"Unexpected processing error: {str(e)}")
        # Cleanup on unexpected errors too
        if extraction_path_str:
             logger.error(f"Cleaning up after unexpected error for extraction at: {extraction_path_str}")
             cleanup_template_directory(Path(extraction_path_str))
             Template.objects.filter(pk=instance.pk).update(extraction_path="") # Clear path
        # Optionally mark inactive
        # Template.objects.filter(pk=instance.pk).update(is_active=False)

@receiver(pre_delete, sender=Template)
def template_pre_delete(sender, instance, **kwargs):
    """
    Signal handler to clean up the template files before deleting the Template instance.
    """
    logger.info(f"Cleaning up directory for Template {instance.pk} before deletion.")
    try:
        # Use the stored extraction path
        if instance.extraction_path:
             cleanup_template_directory(Path(instance.extraction_path)) # Use Path object
        else:
             logger.warning(f"No extraction path found for Template {instance.pk}, cannot perform cleanup.")
    except Exception as e:
        # Log cleanup errors but don't prevent deletion
        logger.error(f"Error during template_pre_delete cleanup for {instance.pk}: {e}", exc_info=True)
        _log_templator_event(EVENT_TEMPLATE_ERROR, instance, 
                             error=f"Error during pre_delete cleanup: {str(e)}") 