import json
import logging
import zipfile
from pathlib import Path
from typing import Dict, Any, Optional, List

import jsonschema
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .exceptions import SchemaValidationError, FileOperationError, InvalidTemplateError
from .constants import METADATA_SCHEMA_FILE, ENGINE_CONFIG_SCHEMA_FILE

logger = logging.getLogger(__name__)

# --- Schema Handling ---

def _load_schema(schema_file_rel_path: str) -> Dict[str, Any]:
    """Loads a JSON schema file relative to the analyzer app directory."""
    try:
        # Construct path relative to this app's directory
        analyzer_app_dir = Path(__file__).resolve().parent
        schema_path = analyzer_app_dir / schema_file_rel_path
        
        if not schema_path.is_file():
            raise FileNotFoundError(f"Schema file not found at {schema_path}")
        
        with open(schema_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError as e:
        logger.error(f"Schema file missing: {e}")
        raise ImproperlyConfigured(f"Required schema file missing: {schema_file_rel_path}") from e
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding schema file {schema_file_rel_path}: {e}")
        raise ImproperlyConfigured(f"Invalid JSON in schema file: {schema_file_rel_path}") from e
    except Exception as e:
        logger.error(f"Unexpected error loading schema {schema_file_rel_path}: {e}")
        raise ImproperlyConfigured(f"Could not load schema file: {schema_file_rel_path}") from e

# Load schemas on module import
METADATA_SCHEMA = _load_schema(METADATA_SCHEMA_FILE)
ENGINE_CONFIG_SCHEMA = _load_schema(ENGINE_CONFIG_SCHEMA_FILE)

def validate_json_schema(data: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
    """Validates dict data against a loaded JSON schema."""
    errors = []
    try:
        validator = jsonschema.Draft7Validator(schema) # Use a specific draft
        validation_errors = sorted(validator.iter_errors(data), key=str)
        
        for error in validation_errors:
            errors.append(f"{' -> '.join(map(str, error.path))}: {error.message}")
            
    except jsonschema.SchemaError as e:
        logger.error(f"Invalid schema provided for validation: {e}")
        # This indicates a problem with the loaded schema itself
        raise ImproperlyConfigured(f"Internal schema error: {e}") from e
    except Exception as e:
        logger.error(f"Unexpected error during schema validation: {e}")
        raise SchemaValidationError(f"Unexpected validation error: {e}") from e
        
    return errors

# --- File I/O --- 

def read_json_file(file_path: Path) -> Optional[Dict[str, Any]]:
    """Safely reads and parses a JSON file."""
    if not file_path.is_file():
        logger.warning(f"JSON file not found: {file_path}")
        return None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in file {file_path}: {e}")
        raise FileOperationError(f"Could not parse JSON file: {file_path}") from e
    except OSError as e:
        logger.error(f"Could not read file {file_path}: {e}")
        raise FileOperationError(f"Could not read file: {file_path}") from e
    except Exception as e:
        logger.error(f"Unexpected error reading JSON file {file_path}: {e}")
        raise FileOperationError(f"Unexpected error reading JSON: {file_path}") from e

def write_json_file(file_path: Path, data: Dict[str, Any]):
    """Safely writes data to a JSON file."""
    try:
        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Successfully wrote JSON file: {file_path}")
    except TypeError as e:
        logger.error(f"Data provided for {file_path} is not JSON serializable: {e}")
        raise FileOperationError(f"Data is not JSON serializable for file: {file_path}") from e
    except OSError as e:
        logger.error(f"Could not write file {file_path}: {e}")
        raise FileOperationError(f"Could not write file: {file_path}") from e
    except Exception as e:
        logger.error(f"Unexpected error writing JSON file {file_path}: {e}")
        raise FileOperationError(f"Unexpected error writing JSON: {file_path}") from e

# --- Dependency Parsing ---

def parse_requirements_txt(file_path: Path) -> List[str]:
    """Parses a requirements.txt file and returns a list of packages.
    Handles basic lines, comments, and ignores options/empty lines.
    Does not handle complex cases like URLs, editable installs, or hashes.
    NOTE: For broader compatibility, consider using a dedicated parsing library.
    """
    dependencies = []
    if not file_path.is_file():
        logger.warning(f"Requirements file not found: {file_path}")
        return dependencies
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Ignore comments and empty lines
                if not line or line.startswith('#'):
                    continue
                # Ignore specific options (simple cases)
                if line.startswith('-'):
                    continue
                # Extract package name (simple split on common version specifiers)
                # This is basic and might not cover all edge cases perfectly.
                package_name = line.split('==')[0].split('>=')[0].split('<=')[0].split('~=')[0].split('!=')[0].split('<')[0].split('>')[0].strip()
                if package_name:
                    dependencies.append(package_name)
    except OSError as e:
        logger.error(f"Could not read requirements file {file_path}: {e}")
        # Don't raise, just return empty list or log error
    except Exception as e:
        logger.error(f"Unexpected error parsing requirements file {file_path}: {e}", exc_info=True)
        
    logger.info(f"Parsed {len(dependencies)} dependencies from {file_path}")
    return dependencies

def parse_package_json(file_path: Path) -> List[str]:
    """Parses a package.json file and returns a list of production dependencies.
    Optionally includes devDependencies if needed in the future.
    """
    dependencies = []
    if not file_path.is_file():
        logger.warning(f"package.json file not found: {file_path}")
        return dependencies
        
    try:
        data = read_json_file(file_path)
        if data:
            # Get production dependencies
            prod_deps = data.get('dependencies', {})
            if isinstance(prod_deps, dict):
                dependencies.extend(list(prod_deps.keys()))
            else:
                logger.warning(f"'dependencies' key in {file_path} is not a dictionary.")
                
            # Optionally include devDependencies (currently commented out)
            # dev_deps = data.get('devDependencies', {})
            # if isinstance(dev_deps, dict):
            #     dependencies.extend(list(dev_deps.keys()))
            # else:
            #      logger.warning(f"'devDependencies' key in {file_path} is not a dictionary.")
                 
            # Remove potential duplicates if devDeps were included
            # dependencies = sorted(list(set(dependencies)))
                 
    except FileOperationError as e:
        # Error already logged by read_json_file
        pass # Expected if file is invalid JSON
    except Exception as e:
        logger.error(f"Unexpected error parsing package.json file {file_path}: {e}", exc_info=True)
        
    logger.info(f"Parsed {len(dependencies)} production dependencies from {file_path}")
    return dependencies

# --- Zip File Handling ---

def extract_zip(zip_path: Path, extract_to: Path, max_size=100*1024*1024):
    """Extracts a zip file safely, checking for total size and zip bombs."""
    total_size = 0
    try:
        extract_to.mkdir(parents=True, exist_ok=True)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Preliminary check for total uncompressed size
            for info in zip_ref.infolist():
                total_size += info.file_size
                if total_size > max_size:
                    raise InvalidTemplateError(f"Zip file exceeds maximum allowed size ({max_size // (1024*1024)}MB)")
            
            # Check for suspicious compression ratios (potential zip bomb)
            # Note: This check is basic. More robust checks might be needed.
            zip_file_size = zip_path.stat().st_size
            if zip_file_size > 0 and total_size / zip_file_size > 100: # Arbitrary ratio limit
                raise InvalidTemplateError("Zip file has an unusually high compression ratio, possibly a zip bomb.")
                
            # Extract safely
            for member in zip_ref.infolist():
                # Prevent path traversal vulnerabilities
                target_path = (extract_to / member.filename).resolve()
                if not target_path.is_relative_to(extract_to.resolve()):
                    raise InvalidTemplateError(f"Attempted path traversal in zip file: {member.filename}")
                
                # Only extract files, skip directories (extractall handles dirs)
                if not member.is_dir():
                    # Create parent directories if needed
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    with zip_ref.open(member, 'r') as source, open(target_path, 'wb') as target:
                        target.write(source.read())
                        
        logger.info(f"Successfully extracted {zip_path} to {extract_to}")

    except zipfile.BadZipFile as e:
        logger.error(f"Invalid or corrupted zip file: {zip_path} - {e}")
        raise InvalidTemplateError(f"Invalid or corrupted zip file: {zip_path}") from e
    except InvalidTemplateError: # Re-raise specific errors
        raise
    except OSError as e:
        logger.error(f"File system error during extraction from {zip_path}: {e}")
        raise FileOperationError(f"Could not extract zip due to OS error: {zip_path}") from e
    except Exception as e:
        logger.error(f"Unexpected error extracting zip {zip_path}: {e}")
        raise InvalidTemplateError(f"Unexpected error during zip extraction: {zip_path}") from e
