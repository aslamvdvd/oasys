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
    # Import analyzer components for secure extraction
    from analyzer.exceptions import InvalidTemplateError, FileOperationError
    HAS_ANALYZER_UTILS = True
    from log_service.logger import log_event
    from log_service.events import LogEventType, EVENT_TEMPLATE_UPLOADED, EVENT_TEMPLATE_DELETED, EVENT_TEMPLATE_ERROR
    HAS_LOG_SERVICE = True
except ImportError as e:
    # Check if it was the analyzer import that failed
    if 'analyzer' in str(e):
        HAS_ANALYZER_UTILS = False
        logger = logging.getLogger(__name__) # Ensure logger is defined
        logger.error("Failed to import exceptions from analyzer.utils. Some error handling might be degraded.")
    else: # Log service import failed
        # Assume analyzer is there if log service failed, but exceptions might be missing
        HAS_ANALYZER_UTILS = True 
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

def extract_template_zip(zip_file_path: Path, extraction_path: Path, max_size=400*1024*1024):
    """
    Extract the ZIP file to the specified path safely.
    - Checks total uncompressed size.
    - Checks compression ratio.
    - Prevents path traversal.
    - Handles nested directories by extracting the contents of a single root directory directly.
    
    Args:
        zip_file_path: Path to the ZIP file
        extraction_path: Path where the ZIP should be extracted
        max_size: Maximum allowed total uncompressed size in bytes. 
                  Defaults to 400 * 1024 * 1024 (400 MB).
        
    Returns:
        True if extraction was successful, raises exception otherwise
    Raises:
        InvalidTemplateError: For zip bombs, path traversal, size limits, bad zip files.
        FileOperationError: For OS-level file errors during extraction/copying.
    """
    total_uncompressed_size = 0
    member_list = []

    try:
        # --- Pre-extraction validation ---
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            member_list = zip_ref.infolist()
            
            # Check total uncompressed size
            for info in member_list:
                total_uncompressed_size += info.file_size
                if total_uncompressed_size > max_size:
                    raise InvalidTemplateError(f"Zip file total uncompressed size exceeds maximum allowed size ({max_size // (1024*1024)}MB)")
            
            # Check compression ratio (basic zip bomb check)
            zip_file_size = zip_file_path.stat().st_size
            # Avoid division by zero for empty zip files; allow if size is 0
            if zip_file_size > 0 and total_uncompressed_size / zip_file_size > 100: # Arbitrary ratio limit
                raise InvalidTemplateError("Zip file has an unusually high compression ratio, possibly a zip bomb.")

        # --- Extraction to temp dir and copy ---
        create_template_directory(extraction_path) # Ensure target exists
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Extract all to temporary directory (already validated members)
            with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                # Note: extractall itself doesn't have traversal protection as strong as manual checks
                # but we validate the final copy step below. Max size/ratio already checked.
                zip_ref.extractall(temp_path)
                
            # Check for single root directory structure
            root_items = list(temp_path.iterdir())
            source_dir = temp_path
            if len(root_items) == 1 and root_items[0].is_dir():
                source_dir = root_items[0] # Use the nested dir as source
                logger.debug(f"Zip contains single root directory '{source_dir.name}', using its contents.")
            else:
                 logger.debug("Zip does not contain single root directory, using root contents.")
            
            # Copy items from source_dir (temp or nested temp) to final extraction_path
            # Apply path traversal check during copy
            final_extraction_path_resolved = extraction_path.resolve()
            for item in source_dir.iterdir():
                dest = extraction_path / item.name
                dest_resolved = dest.resolve()
                
                # --- Path Traversal Check during copy ---
                if not dest_resolved.is_relative_to(final_extraction_path_resolved):
                     # Log the attempt before raising
                     _log_templator_event(EVENT_TEMPLATE_ERROR, template=None, 
                                         error=f"Path traversal attempt detected during copy: source='{item}', intended_dest='{dest}'", 
                                         details=f"Resolved dest '{dest_resolved}' not relative to '{final_extraction_path_resolved}'")
                     raise InvalidTemplateError(f"Attempted path traversal during file copy: {item.name}")
                     
                # Perform the copy
                try:
                    if item.is_dir(): 
                        shutil.copytree(item, dest, dirs_exist_ok=True)
                    else: 
                        shutil.copy2(item, dest)
                except OSError as copy_err:
                    _log_templator_event(EVENT_TEMPLATE_ERROR, template=None, error=f"OS Error copying item {item.name} to {dest}: {copy_err}")
                    raise FileOperationError(f"Error copying extracted file '{item.name}': {copy_err}") from copy_err
                    
        logger.info(f"Successfully extracted and copied zip {zip_file_path} to {extraction_path}")
        return True

    except zipfile.BadZipFile as e:
        _log_templator_event(EVENT_TEMPLATE_ERROR, template=None, error=f"Invalid/corrupted zip file: {zip_file_path} - {e}")
        raise InvalidTemplateError(f"Invalid or corrupted zip file: {zip_file_path}") from e
    except InvalidTemplateError as e: # Catch specific validation errors
        _log_templator_event(EVENT_TEMPLATE_ERROR, template=None, error=f"Zip validation failed for {zip_file_path}: {e}")
        raise # Re-raise to be caught by caller
    except FileOperationError as e: # Catch specific file operation errors
        _log_templator_event(EVENT_TEMPLATE_ERROR, template=None, error=f"File operation error during extraction {zip_file_path}: {e}")
        raise # Re-raise
    except OSError as e: # Catch potential OS errors from file ops or tempfile creation
         _log_templator_event(EVENT_TEMPLATE_ERROR, template=None, error=f"OS Error during extraction process for {zip_file_path}: {e}")
         # Wrap in FileOperationError if possible
         exc_class = FileOperationError if HAS_ANALYZER_UTILS else OSError
         raise exc_class(f"OS Error during extraction process: {e}") from e
    except Exception as e:
        _log_templator_event(EVENT_TEMPLATE_ERROR, template=None, error=f"Unexpected error extracting zip {zip_file_path}: {str(e)}")
        # Clean up partially extracted files on generic exceptions
        if extraction_path.exists():
            logger.error(f"Cleaning up target directory {extraction_path} after unexpected error.")
            try: 
                shutil.rmtree(extraction_path)
            except Exception as cleanup_e:
                 _log_templator_event(EVENT_TEMPLATE_ERROR, template=None, error=f"Target directory cleanup failed: {str(cleanup_e)}")
        # Wrap in InvalidTemplateError if possible
        exc_class = InvalidTemplateError if HAS_ANALYZER_UTILS else Exception
        raise exc_class(f"Unexpected error during zip extraction: {zip_file_path}") from e

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
            # Use FileOperationError if available, otherwise standard OSError
            exc_class = FileOperationError if HAS_ANALYZER_UTILS else OSError
            raise exc_class(f"Failed to clean existing directory: {extraction_path}") from e
            
    # Use the local, secured extraction function
    try:
        extract_template_zip(Path(zip_file_path), extraction_path)
    except (InvalidTemplateError, FileOperationError) as e:
        # Errors are logged within extract_template_zip
        # Re-raise to be caught by the signal handler for cleanup/logging
        raise e
    
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