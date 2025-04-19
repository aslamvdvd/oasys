import os
import zipfile
import shutil
import logging
import tempfile
from pathlib import Path
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

# Import log service components
try:
    from log_service.logger import log_event
    from log_service.events import LogEventType, EVENT_TEMPLATE_UPLOADED, EVENT_TEMPLATE_DELETED, EVENT_TEMPLATE_ERROR
    HAS_LOG_SERVICE = True
except ImportError:
    HAS_LOG_SERVICE = False
    # Dummy logger for fallback
    logger = logging.getLogger(__name__)
    def log_event(channel, data): logger.warning(f"Log service unavailable. Event: {channel}, Data: {data}")

# Use logger even if log_service is available for internal debug/info
logger = logging.getLogger(__name__)

# --- Central Logging Helper --- 

def _log_templator_event(event_type: str, template, **extra_data):
    """
    Central helper for logging templator-related events.
    Uses the correct LogEventType Enum.
    """
    log_data = {
        'event': event_type,
        **extra_data
    }
    if template:
        log_data.update({
            'template_id': template.id,
            'template_name': template.name,
            'category': template.category.name if template.category else 'None',
            'user_id': template.uploaded_by.id if template.uploaded_by else None,
            'username': template.uploaded_by.username if template.uploaded_by else 'unknown',
        })
        if 'extraction_path' not in log_data and hasattr(template, 'extraction_path') and template.extraction_path:
             log_data['extraction_path'] = str(template.extraction_path)

    if HAS_LOG_SERVICE:
        log_event(LogEventType.TEMPLATOR, log_data)
        log_event(LogEventType.TEMPLATOR_ACTIVITY, log_data)
    else:
        log_level = logging.ERROR if 'error' in event_type else logging.INFO
        logger.log(log_level, f"Fallback Templator Log: {event_type} - Data: {log_data}")

# --- File/Directory Operations --- 

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
        _log_templator_event(EVENT_TEMPLATE_ERROR, template=None, error=f"Failed to create dir {path}: {str(e)}")
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
    all_entries = []
    try:
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            all_entries = [item.filename for item in zip_ref.infolist()]
            folder_exists = {}
            for required in required_folders:
                direct_match = any(entry.startswith(f"{required}/") for entry in all_entries)
                nested_match = any(f"/{required}/" in entry or entry.endswith(f"/{required}/") for entry in all_entries)
                folder_exists[required] = direct_match or nested_match
            missing_folders = [folder for folder, exists in folder_exists.items() if not exists]
            if missing_folders:
                missing = ', '.join(missing_folders)
                _log_templator_event(EVENT_TEMPLATE_ERROR, template=None, 
                                     error=f"ZIP validation failed - missing folders: {missing}",
                                     zip_structure=f"{all_entries[:10]}...")
                raise ValidationError(_(f"The ZIP file is missing required folders: {missing}"))
            return True
    except zipfile.BadZipFile:
        raise ValidationError(_("The uploaded file is not a valid ZIP archive."))
    except ValidationError:
        raise
    except Exception as e:
        _log_templator_event(EVENT_TEMPLATE_ERROR, template=None, error=f"Error validating ZIP: {str(e)}")
        raise ValidationError(_("An error occurred while validating the ZIP file."))

def extract_template_zip(zip_file_path, extraction_path):
    """
    Extract the ZIP file to the specified path.
    Handle nested directories by extracting the contents of the root directory directly.
    
    Args:
        zip_file_path: Path to the ZIP file
        extraction_path: Path where the ZIP should be extracted
        
    Returns:
        True if extraction was successful, raises exception otherwise
    """
    try:
        create_template_directory(extraction_path)
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                zip_ref.extractall(temp_path)
            root_items = list(temp_path.iterdir())
            if len(root_items) == 1 and root_items[0].is_dir():
                root_dir = root_items[0]
                for item in root_dir.iterdir():
                    dest = extraction_path / item.name
                    if item.is_dir(): shutil.copytree(item, dest, dirs_exist_ok=True)
                    else: shutil.copy2(item, dest)
            else:
                for item in root_items:
                    dest = extraction_path / item.name
                    if item.is_dir(): shutil.copytree(item, dest, dirs_exist_ok=True)
                    else: shutil.copy2(item, dest)
        return True
    except Exception as e:
        _log_templator_event(EVENT_TEMPLATE_ERROR, template=None, error=f"Failed to extract ZIP: {str(e)}")
        if extraction_path.exists():
            try: shutil.rmtree(extraction_path)
            except Exception as cleanup_e:
                 _log_templator_event(EVENT_TEMPLATE_ERROR, template=None, error=f"Cleanup failed: {str(cleanup_e)}")
        raise

def process_template_upload(template):
    """
    Process a template upload, primarily handling extraction.
    Structural validation is deferred to the analyzer app.
    
    Args:
        template: Template model instance
        
    Returns:
        Path where the template was extracted
    """
    zip_file_path = template.zip_file.path
    # Removed call to validate_zip_contents(zip_file_path) - Defer validation to analyzer
    logger.info(f"Starting extraction process for {zip_file_path}")
    extraction_path = get_template_extraction_path(template.category.slug, template.slug)
    
    # Ensure the target directory is clean before extraction
    if extraction_path.exists():
        logger.warning(f"Extraction path {extraction_path} already exists. Cleaning up before extraction.")
        try:
            shutil.rmtree(extraction_path)
        except OSError as e:
            _log_templator_event(EVENT_TEMPLATE_ERROR, template, error=f"Failed to clean up existing extraction directory {extraction_path}: {str(e)}")
            raise FileOperationError(f"Failed to clean existing directory: {extraction_path}") from e
            
    extract_template_zip(zip_file_path, extraction_path) # Extract the zip
    logger.info(f"Successfully extracted {zip_file_path} to {extraction_path}")
    # Log the upload event (without framework info here, analyzer will log details)
    # _log_templator_event(EVENT_TEMPLATE_UPLOADED, template, extraction_path=str(extraction_path))
    return extraction_path

def cleanup_template_directory(extraction_path: Path):
    """
    Remove a template's extracted files directory.
    Now accepts the path directly.
    
    Args:
        extraction_path: The Path object for the directory to remove.
    """
    # Use the extraction_path directly (passed from signal)
    if extraction_path and extraction_path.exists() and extraction_path.is_dir():
        try:
            shutil.rmtree(extraction_path)
            logger.info(f"Successfully cleaned up directory: {extraction_path}")
            # Logging the deletion event might be better handled in the signal or based on analyzer results
            # _log_templator_event(EVENT_TEMPLATE_DELETED, template, extraction_path=str(extraction_path))
        except Exception as e:
            logger.error(f"Failed to delete directory {extraction_path}: {str(e)}")
            # Optionally log this using _log_templator_event if needed, but might require template instance
    elif extraction_path:
        logger.warning(f"Cleanup requested for path {extraction_path}, but it does not exist or is not a directory.")

# --- Deprecated/Removed --- 
# validate_zip_contents is no longer called by process_template_upload
# The logic is now handled by the analyzer app.

# def validate_zip_contents(zip_file):
#     """
#     DEPRECATED: Validation moved to analyzer app.
#     Validate that the uploaded ZIP file contains required folders.
#     ...
#     """
#     # ... (original implementation commented out or removed)
#     pass 