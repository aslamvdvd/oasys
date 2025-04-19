# Core validator logic 

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from .constants import (
    Framework, Engine,
    METADATA_FILENAME, ENGINE_CONFIG_FILENAME,
    TEMPLATE_DIR_NAME, STATIC_DIR_NAME,
    STATUS_SUCCESS, STATUS_ERROR
)
from .exceptions import (
    AnalyzerError, InvalidTemplateError, MetadataError, SchemaValidationError, FileOperationError
)
from .utils import (
    read_json_file, write_json_file, validate_json_schema,
    METADATA_SCHEMA, ENGINE_CONFIG_SCHEMA,
    parse_requirements_txt, parse_package_json
)
from .framework_detector import detect_framework

logger = logging.getLogger(__name__)

class TemplateValidator:
    """Validates extracted template content and generates config files."""

    def __init__(self, extracted_path: Path, template_info: Optional[Dict[str, Any]] = None):
        """
        Initializes the validator.

        Args:
            extracted_path: Path to the root directory of the extracted template content.
            template_info: Optional dictionary containing pre-existing template info 
                             (e.g., from the Template model in templator app), 
                             like name, slug, category, author, potentially framework.
        """
        if not extracted_path.is_dir():
            raise FileNotFoundError(f"Extracted template path does not exist: {extracted_path}")
            
        self.extracted_path = extracted_path
        self.template_info = template_info or {}
        self.results = {
            "status": STATUS_SUCCESS,
            "framework": Framework.UNKNOWN.value,
            "metadata_path": str(self.extracted_path / METADATA_FILENAME),
            "engine_config_path": str(self.extracted_path / ENGINE_CONFIG_FILENAME),
            "warnings": [],
            "errors": [],
        }
        self.metadata = None
        self.metadata_existed = False # Flag to track if file existed beforehand
        self.detected_framework = Framework.UNKNOWN
        self.detected_engine = Engine.STATIC

    def _add_error(self, message: str, exception: Optional[Exception] = None):
        """Adds an error message to the results and logs it."""
        self.results["status"] = STATUS_ERROR
        self.results["errors"].append(message)
        log_message = f"Validation Error: {message}" 
        if exception:
            log_message += f" - Exception: {exception}"
            logger.error(log_message, exc_info=isinstance(exception, AnalyzerError))
        else:
            logger.error(log_message)

    def _add_warning(self, message: str):
        """Adds a warning message to the results and logs it."""
        self.results["warnings"].append(message)
        logger.warning(f"Validation Warning: {message}")

    def _validate_structure(self):
        """Performs basic structural checks (e.g., presence of template/static dirs)."""
        logger.info("Validating basic structure...")
        template_dir = self.extracted_path / TEMPLATE_DIR_NAME
        static_dir = self.extracted_path / STATIC_DIR_NAME

        # Check for required directories (can be warnings or errors depending on strictness)
        if not template_dir.is_dir():
            self._add_warning(f"Missing recommended '{TEMPLATE_DIR_NAME}' directory.")
            # Could be an error depending on framework requirements
            # self._add_error(f"Required '{TEMPLATE_DIR_NAME}' directory is missing.")
        
        if not static_dir.is_dir():
             self._add_warning(f"Missing recommended '{STATIC_DIR_NAME}' directory.")
             # Could be an error depending on framework requirements
             # self._add_error(f"Required '{STATIC_DIR_NAME}' directory is missing.")

    def _process_metadata(self):
        """Loads, validates, and potentially generates metadata.json."""
        logger.info("Processing metadata...")
        metadata_path = self.extracted_path / METADATA_FILENAME
        self.metadata = None
        self.metadata_existed = False # Flag to track if file existed beforehand
        generate_new = False
        validation_errors = []

        try:
            existing_metadata = read_json_file(metadata_path)
            if existing_metadata:
                self.metadata_existed = True # Mark that it existed
                self.metadata = existing_metadata
                self._add_warning(f"Found existing {METADATA_FILENAME}. Validating...")
                validation_errors = validate_json_schema(self.metadata, METADATA_SCHEMA)
                if validation_errors:
                    msg = f"Existing {METADATA_FILENAME} is invalid."
                    self._add_error(msg + " Errors: " + '; '.join(validation_errors), SchemaValidationError(errors=validation_errors))
                    self._add_warning(f"Discarding invalid {METADATA_FILENAME} and generating a new one.")
                    generate_new = True
                    self.metadata = None # Reset metadata
                else:
                    logger.info(f"Existing {METADATA_FILENAME} is valid.")
            else:
                self._add_warning(f"{METADATA_FILENAME} not found. Generating a new one.")
                generate_new = True

        except FileOperationError as e:
            self._add_error(f"Could not read existing {METADATA_FILENAME}: {e}", e)
            generate_new = True

        if generate_new:
            self._generate_metadata()
            # Re-validate the generated metadata (should always pass if generation is correct)
            if self.metadata:
                 validation_errors = validate_json_schema(self.metadata, METADATA_SCHEMA)
                 if validation_errors:
                      # This indicates a bug in _generate_metadata or the schema
                      self._add_error(f"INTERNAL ERROR: Generated {METADATA_FILENAME} failed validation: {validation_errors}", SchemaValidationError(errors=validation_errors))

    def _generate_metadata(self):
        """Generates a default metadata.json file based on available info."""
        logger.info(f"Generating default {METADATA_FILENAME}...")
        # Use detected framework if available, otherwise keep it unknown for now
        framework_value = self.detected_framework.value if self.detected_framework != Framework.UNKNOWN else "unknown"
        
        # Try to get info from the template model passed during init
        # Use defaults if not provided
        generated_meta = {
            "name": self.template_info.get('name', self.extracted_path.name), # Use folder name as fallback
            "slug": self.template_info.get('slug', self.extracted_path.name),
            "framework": self.template_info.get('framework', framework_value), # Prefer provided info
            "category": self.template_info.get('category_slug', 'uncategorized'), # Assuming category obj has slug
            "author": self.template_info.get('author_username', 'system'), # Assuming user obj has username
            "version": self.template_info.get('version', "1.0")
        }
        
        # Update the instance metadata
        self.metadata = generated_meta
        
        # Attempt to write the file
        metadata_path = self.extracted_path / METADATA_FILENAME
        try:
            write_json_file(metadata_path, self.metadata)
            logger.info(f"Successfully generated and wrote {METADATA_FILENAME}")
        except FileOperationError as e:
            self._add_error(f"Failed to write generated {METADATA_FILENAME}: {e}", e)
            self.metadata = None # Invalidate if write failed

    def _detect_and_update_framework(self):
        """Detects framework if not specified or invalid/unknown in metadata."""
        logger.info("Detecting framework...")
        update_meta = False
        run_detection = True # Default to running detection
        framework_from_metadata = Framework.UNKNOWN

        # Check if valid, non-unknown framework exists in PRE-EXISTING metadata
        if self.metadata_existed and self.metadata and 'framework' in self.metadata:
            framework_str = self.metadata.get('framework', Framework.UNKNOWN.value).lower()
            try:
                framework_enum_val = Framework(framework_str)
                # Only skip detection if metadata existed AND contained a valid, non-unknown framework
                if framework_enum_val != Framework.UNKNOWN:
                    logger.info(f"Using valid framework '{framework_enum_val.value}' from pre-existing metadata.")
                    self.detected_framework = framework_enum_val
                    self.detected_engine = self._get_engine_for_framework(self.detected_framework)
                    self.results["framework"] = self.detected_framework.value
                    run_detection = False # Don't run detection
                else:
                    self._add_warning(f"Pre-existing {METADATA_FILENAME} had framework set to '{framework_enum_val.value}'. Running detection.")
            except ValueError:
                self._add_warning(f"Invalid framework '{framework_str}' specified in pre-existing {METADATA_FILENAME}. Running detection.")
        elif self.metadata: # Metadata was generated or existed but had no framework field
            self._add_warning(f"Metadata was generated or missing framework field. Running detection.")
        else: # No metadata at all (shouldn't happen if _process_metadata ran)
             self._add_warning(f"No metadata found before framework detection. Running detection.")

        # Run detection if needed
        if run_detection:
            try:
                detected_fw, detected_eng = detect_framework(self.extracted_path)
                logger.info(f"Detection function returned: Framework={detected_fw.value}, Engine={detected_eng.value}")
                
                # Check if detection differs from what might have been in metadata (even if unknown)
                original_meta_framework_enum = Framework.UNKNOWN
                if self.metadata and self.metadata.get('framework'):
                    try:
                        original_meta_framework_enum = Framework(self.metadata.get('framework').lower())
                    except ValueError:
                        pass # Ignore invalid value

                # Update internal state
                self.detected_framework = detected_fw
                self.detected_engine = detected_eng
                self.results["framework"] = self.detected_framework.value
                logger.info(f"Stored detected framework: {self.results['framework']}")

                # Mark metadata for update if detection result differs from original OR if metadata was just generated
                if detected_fw != original_meta_framework_enum or not self.metadata_existed:
                    self._add_warning(f"Framework detection result ({self.detected_framework.value}) requires metadata update.")
                    update_meta = True
                    if self.metadata: # Update in-memory dict if it exists
                        self.metadata['framework'] = self.detected_framework.value
                        logger.info(f"Updated self.metadata in memory with framework: {self.metadata['framework']}")
                    else: # Metadata needs to be generated (or regenerated)
                         logger.info("Generating/Regenerating metadata with detected framework.")
                         self._generate_metadata() # Regenerate with the correct framework
                         # Ensure update_meta is false now since we just wrote the file
                         update_meta = False 
                         
            except FileNotFoundError as e:
                 self._add_error(f"Extracted path disappeared during analysis: {e}", e)
            except Exception as e:
                 logger.exception(f"Framework detection failed unexpectedly: {e}")
                 self._add_error(f"Framework detection failed: {e}", e)
                 # Fallback to unknown
                 self.detected_framework = Framework.UNKNOWN
                 self.detected_engine = Engine.STATIC
                 self.results["framework"] = self.detected_framework.value
                 logger.warning("Fell back to UNKNOWN framework due to error during detection.")
                 if self.metadata and self.metadata.get('framework') != Framework.UNKNOWN.value:
                     # If metadata existed with a different value, update it to UNKNOWN
                     self.metadata['framework'] = self.detected_framework.value
                     update_meta = True
        
        # If metadata existed and needs updating (e.g., fallback after error, or original was invalid)
        if update_meta and self.metadata:
            # This block handles cases where metadata existed but needs updating *after* detection logic
            metadata_path = self.extracted_path / METADATA_FILENAME
            logger.info(f"Attempting final write of updated metadata with framework: {self.metadata.get('framework')}")
            try:
                write_json_file(metadata_path, self.metadata)
                logger.info(f"Successfully wrote final updated {METADATA_FILENAME}")
            except FileOperationError as e:
                self._add_error(f"Failed to write final updated {METADATA_FILENAME}: {e}", e)

    def _get_engine_for_framework(self, framework: Framework) -> Engine:
        """Maps a framework to its typical engine/runtime."""
        if framework in [Framework.DJANGO, Framework.FLASK]:
            return Engine.PYTHON_3_11
        elif framework in [Framework.REACT, Framework.VUE, Framework.ANGULAR]: # Added Angular
            return Engine.NODE_18
        elif framework == Framework.HTML:
            return Engine.STATIC
        else:
            # Default for UNKNOWN or other cases
            logger.warning(f"No specific engine mapping for framework '{framework.value}'. Defaulting to STATIC.")
            return Engine.STATIC

    def _generate_engine_config(self):
        """Generates the engine_config.json file based on detected framework."""
        logger.info(f"Generating {ENGINE_CONFIG_FILENAME}... Using detected framework: {self.detected_framework.value}")
        engine_config_path = self.extracted_path / ENGINE_CONFIG_FILENAME
        
        entry_point = None
        static_dir = None
        dependencies = []

        # --- Determine Static Directory (Best Guess - runs first as it's generic) ---
        potential_static_dirs = [ "assets", "static", "public" ] 
        for potential_dir in potential_static_dirs:
            if (self.extracted_path / potential_dir).is_dir():
                static_dir = potential_dir
                logger.info(f"Found potential static directory: {static_dir}")
                break
        if not static_dir:
            static_dir = STATIC_DIR_NAME # Fallback to default 'static'
            self._add_warning(f"Could not find common static directory ({', '.join(potential_static_dirs)}). Defaulting to '{static_dir}'.")

        # --- Determine Entry Point & Dependencies (Framework Specific) ---
        fw = self.detected_framework
        engine = self.detected_engine

        if fw in [Framework.HTML, Framework.REACT, Framework.VUE, Framework.ANGULAR]:
            # For HTML and JS frameworks, find the primary HTML file
            potential_entries = [
                "index.html",                   # Common for static/root apps/builds
                "index.htm",                    # Alternative static entry
                "src/index.html",               # Common source location for Angular/others
                "src/index.htm" 
            ]
            for potential in potential_entries:
                if (self.extracted_path / potential).is_file():
                    entry_point = potential
                    logger.info(f"Found potential web entry point: {entry_point}")
                    break
            if not entry_point:
                entry_point = "index.html" # Default for web serving if nothing else found
                self._add_warning(f"Could not find standard web entry point ({', '.join(potential_entries)}). Defaulting to '{entry_point}'.")
            
            # JS frameworks also have dependencies
            if engine == Engine.NODE_18:
                pkg_path = self.extracted_path / "package.json"
                if pkg_path.is_file():
                    dependencies = parse_package_json(pkg_path)
                else:
                    self._add_warning(f"Node engine detected but package.json not found.")
                    
        elif fw == Framework.DJANGO:
            # Look for wsgi.py or asgi.py
            potential_entries = ["wsgi.py", "asgi.py"]
            # Usually inside a project sub-directory named same as parent or 'src'
            project_dirs = [d for d in self.extracted_path.iterdir() if d.is_dir() and d.name != '__pycache__']
            project_dir_paths = [self.extracted_path / d.name for d in project_dirs] + [self.extracted_path] # Check root too
            
            found = False
            for p_dir in project_dir_paths:
                for potential in potential_entries:
                     if (p_dir / potential).is_file():
                        entry_point = str((p_dir / potential).relative_to(self.extracted_path))
                        logger.info(f"Found potential Django entry point: {entry_point}")
                        found = True
                        break
                if found: break
            
            if not entry_point:
                self._add_warning(f"Could not find Django entry point ({potential_entries[0]}, {potential_entries[1]}) in common locations.")
            
            # Look for requirements.txt
            req_path = self.extracted_path / "requirements.txt"
            if req_path.is_file():
                dependencies = parse_requirements_txt(req_path)
            else: 
                self._add_warning("Django project detected but no root requirements.txt found.")

        elif fw == Framework.FLASK:
            # Look for app.py or wsgi.py at the root
            potential_entries = ["app.py", "wsgi.py"]
            for potential in potential_entries:
                if (self.extracted_path / potential).is_file():
                    entry_point = potential
                    logger.info(f"Found potential Flask entry point: {entry_point}")
                    break
            if not entry_point:
                 self._add_warning(f"Could not find common Flask entry point ({potential_entries[0]}, {potential_entries[1]}) at root.")

            # Look for requirements.txt
            req_path = self.extracted_path / "requirements.txt"
            if req_path.is_file():
                dependencies = parse_requirements_txt(req_path)
            else: 
                self._add_warning("Flask project detected but no root requirements.txt found.")

        else: # Includes Framework.UNKNOWN
            logger.warning(f"Cannot determine specific entry point or dependencies for framework: {fw.value}")
            # Attempt to find a default index.html anyway for basic serving possibility
            if (self.extracted_path / "index.html").is_file(): entry_point = "index.html"
            elif (self.extracted_path / "index.htm").is_file(): entry_point = "index.htm"
                
        # --- Assemble Config Data ---          
        config_data = {
            "entry_point": entry_point, # Can be None
            "static_dir": static_dir, 
            "runtime": self.detected_engine.value,
            "dependencies": dependencies, 
            "framework": self.detected_framework.value,
            "author": self.template_info.get('author_username', None) 
        }
        logger.debug(f"Generated engine config data: {config_data}")

        # --- Validate and Write --- 
        validation_errors = validate_json_schema(config_data, ENGINE_CONFIG_SCHEMA)
        if validation_errors:
            self._add_error(f"INTERNAL ERROR: Generated {ENGINE_CONFIG_FILENAME} failed validation: {validation_errors}", SchemaValidationError(errors=validation_errors))
            return
        try:
            write_json_file(engine_config_path, config_data)
            logger.info(f"Successfully generated and wrote {ENGINE_CONFIG_FILENAME}")
        except FileOperationError as e:
            self._add_error(f"Failed to write generated {ENGINE_CONFIG_FILENAME}: {e}", e)

    def validate(self) -> Dict[str, Any]:
        """Runs the full validation and generation process."""
        logger.info(f"--- Starting Validation for {self.extracted_path} ---")
        try:
            # 1. Basic structure checks
            self._validate_structure()
            
            # 2. Process metadata (load/validate existing or generate default)
            # This step might set self.metadata
            self._process_metadata()
            
            # 3. Detect framework (if needed) and update metadata if required
            # This sets self.detected_framework, self.detected_engine and potentially updates self.metadata
            self._detect_and_update_framework()
            
            # Ensure metadata framework matches final detected framework if metadata was generated/updated
            if self.metadata and self.metadata.get('framework') != self.detected_framework.value:
                self._add_warning("Metadata framework differs from final detected framework. Ensure metadata is updated if necessary.")
                # Potentially force metadata update here if needed, though _detect_and_update_framework should handle most cases

            # 4. Generate engine config based on detected framework/engine
            self._generate_engine_config()

        except AnalyzerError as e:
            # Catch specific analyzer errors
            self._add_error(f"Validation failed: {e}", e)
        except Exception as e:
            # Catch unexpected errors
            logger.exception(f"Unexpected error during validation of {self.extracted_path}")
            self._add_error(f"An unexpected error occurred: {e}", e)
            
        logger.info(f"--- Validation Finished for {self.extracted_path} with status: {self.results['status']} ---")
        return self.results

# --- Convenience Function --- 

def validate_template(extracted_path: Path, template_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Convenience function to instantiate and run the validator."""
    try:
        validator = TemplateValidator(extracted_path, template_info)
        return validator.validate()
    except FileNotFoundError as e:
        logger.error(f"Cannot validate template, path not found: {e}")
        return {
            "status": STATUS_ERROR,
            "framework": Framework.UNKNOWN.value,
            "metadata_path": None,
            "engine_config_path": None,
            "warnings": [],
            "errors": [f"Extracted template path not found: {extracted_path}"],
        }
    except Exception as e:
        logger.exception(f"Failed to initialize validator for {extracted_path}: {e}")
        return {
            "status": STATUS_ERROR,
            "framework": Framework.UNKNOWN.value,
            "metadata_path": None,
            "engine_config_path": None,
            "warnings": [],
            "errors": [f"Failed to initialize validator: {e}"],
        } 