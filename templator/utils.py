import os
import zipfile
import shutil
from pathlib import Path
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

# Try to import log_service if available
try:
    from log_service import log_event
    HAS_LOG_SERVICE = True
except ImportError:
    HAS_LOG_SERVICE = False
    import logging
    logger = logging.getLogger(__name__)

def get_template_extraction_path(category_slug, template_slug):
    """
    Get the full path where template files should be extracted.
    
    Args:
        category_slug: Slug of the template category
        template_slug: Slug of the template
        
    Returns:
        Path object pointing to the extraction directory
    """
    base_path = Path(settings.TEMPLATE_UPLOAD_PATH)
    return base_path / category_slug / template_slug

def create_template_directory(path):
    """
    Creates the directory structure for the template.
    
    Args:
        path: Path to create
        
    Returns:
        True if directory was created or already exists, raises exception otherwise
    """
    try:
        path.mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        _log_error(f"Failed to create template directory {path}: {str(e)}")
        raise

def validate_zip_contents(zip_file):
    """
    Validate that the uploaded ZIP file contains required folders.
    
    Args:
        zip_file: Path to the uploaded ZIP file
        
    Returns:
        True if valid, raises ValidationError otherwise
    """
    required_folders = ['static', 'templates']
    
    try:
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            # Get a list of all directories in the zip
            directories = {item.filename.split('/')[0] for item in zip_ref.infolist() 
                          if item.filename.endswith('/') or '/' in item.filename}
            
            # Check if all required folders exist
            missing_folders = [folder for folder in required_folders if folder not in directories]
            
            if missing_folders:
                missing = ', '.join(missing_folders)
                raise ValidationError(_(f"The ZIP file is missing required folders: {missing}"))
            
            return True
    except zipfile.BadZipFile:
        raise ValidationError(_("The uploaded file is not a valid ZIP archive."))
    except Exception as e:
        _log_error(f"Error validating ZIP contents: {str(e)}")
        raise ValidationError(_("An error occurred while validating the ZIP file."))

def extract_template_zip(zip_file_path, extraction_path):
    """
    Extract the ZIP file to the specified path.
    
    Args:
        zip_file_path: Path to the ZIP file
        extraction_path: Path where the ZIP should be extracted
        
    Returns:
        True if extraction was successful, raises exception otherwise
    """
    try:
        # Create the extraction directory
        create_template_directory(extraction_path)
        
        # Extract the ZIP file
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            zip_ref.extractall(extraction_path)
            
        return True
    except Exception as e:
        _log_error(f"Failed to extract template ZIP: {str(e)}")
        # Clean up any partially extracted files
        if extraction_path.exists():
            try:
                shutil.rmtree(extraction_path)
            except Exception:
                pass
        raise

def process_template_upload(template):
    """
    Process a template upload, including validation and extraction.
    
    Args:
        template: Template model instance
        
    Returns:
        Path where the template was extracted
    """
    zip_file_path = template.zip_file.path
    
    # Validate the ZIP contents
    validate_zip_contents(zip_file_path)
    
    # Get the extraction path
    extraction_path = get_template_extraction_path(template.category.slug, template.slug)
    
    # Extract the ZIP file
    extract_template_zip(zip_file_path, extraction_path)
    
    # Log the successful extraction
    _log_success(template, extraction_path)
    
    return extraction_path

def _log_success(template, extraction_path):
    """
    Log a successful template upload and extraction.
    
    Args:
        template: The Template instance
        extraction_path: Path where the template was extracted
    """
    log_data = {
        'event': 'template_uploaded',
        'template_id': template.id,
        'template_name': template.name,
        'category': template.category.name,
        'user_id': template.uploaded_by.id if template.uploaded_by else None,
        'username': template.uploaded_by.username if template.uploaded_by else 'unknown',
        'extraction_path': str(extraction_path)
    }
    
    if HAS_LOG_SERVICE:
        # Log to both templator.log and the general templator_activity log
        log_event('templator', log_data)
        log_event('templator_activity', log_data)
    else:
        logger.info(f"Template '{template.name}' uploaded successfully and extracted to {extraction_path}")

def _log_error(error_message):
    """
    Log an error that occurred during template processing.
    
    Args:
        error_message: Description of the error
    """
    log_data = {
        'event': 'template_error',
        'error': error_message
    }
    
    if HAS_LOG_SERVICE:
        # Log to both templator.log and the general templator_activity log
        log_event('templator', log_data)
        log_event('templator_activity', log_data)
    else:
        logger.error(error_message)

def cleanup_template_directory(template):
    """
    Remove a template's extracted files when the template is deleted.
    
    Args:
        template: The Template instance being deleted
    """
    if not template.extraction_path:
        return
    
    extraction_path = Path(template.extraction_path)
    if extraction_path.exists():
        try:
            shutil.rmtree(extraction_path)
            log_data = {
                'event': 'template_deleted',
                'template_id': template.id,
                'template_name': template.name,
                'category': template.category.name,
                'user_id': template.uploaded_by.id if template.uploaded_by else None,
                'username': template.uploaded_by.username if template.uploaded_by else 'unknown',
                'extraction_path': str(extraction_path)
            }
            
            if HAS_LOG_SERVICE:
                log_event('templator', log_data)
                log_event('templator_activity', log_data)
            else:
                logger.info(f"Template directory {extraction_path} deleted")
        except Exception as e:
            _log_error(f"Failed to delete template directory {extraction_path}: {str(e)}") 