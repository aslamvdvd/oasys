# Logic for detecting the template framework 

import logging
import json
from pathlib import Path
from typing import Tuple, Optional

from .constants import Framework, Engine
from .utils import read_json_file
from .exceptions import FrameworkDetectionError

logger = logging.getLogger(__name__)

# --- Detection Rules ---

# File/Dir Existence Checks
DJANGO_FILES = ["manage.py", "settings.py", "wsgi.py", "asgi.py"]
FLASK_FILES = ["app.py", "wsgi.py"] # Less definitive
REACT_INDICATORS = ["package.json", "src", "public"]

# Content Checks (basic keyword spotting)
FLASK_KEYWORDS = [b"from flask import Flask", b"app = Flask(__name__)"]

# --- Detector Functions ---

def _check_django(extracted_path: Path) -> bool:
    """Check for characteristic Django file/directory structure."""
    # Simplistic check: look for manage.py or a settings.py
    # A more robust check might look inside project subdirectories
    if (extracted_path / "manage.py").is_file():
        return True
    # Look for settings.py within potential project directories
    for item in extracted_path.iterdir():
        if item.is_dir() and (item / "settings.py").is_file():
            return True
    return False

def _check_react(extracted_path: Path) -> bool:
    """Check for characteristic React project structure and package.json."""
    package_json_path = extracted_path / "package.json"
    if not package_json_path.is_file():
        return False
    
    try:
        pkg_data = read_json_file(package_json_path)
        if pkg_data and (
            ("dependencies" in pkg_data and "react" in pkg_data["dependencies"]) or \
            ("devDependencies" in pkg_data and "react" in pkg_data["devDependencies"])
        ):
            # Check for src/public dirs as well for higher confidence
            if (extracted_path / "src").is_dir() or (extracted_path / "public").is_dir():
                return True
    except Exception as e:
        logger.warning(f"Could not read or parse package.json for React check: {e}")
        
    return False

def _check_vue(extracted_path: Path) -> bool:
    """Check for characteristic Vue project structure and package.json."""
    package_json_path = extracted_path / "package.json"
    if not package_json_path.is_file():
        return False
    
    try:
        pkg_data = read_json_file(package_json_path)
        if pkg_data and (
            ("dependencies" in pkg_data and "vue" in pkg_data["dependencies"]) or \
            ("devDependencies" in pkg_data and "vue" in pkg_data["devDependencies"])
        ):
            # Optional: Look for src/App.vue or main.js/ts for higher confidence
            if (extracted_path / "src" / "App.vue").is_file() or \
               (extracted_path / "src" / "main.js").is_file() or \
               (extracted_path / "src" / "main.ts").is_file():
                logger.debug("_check_vue: Found vue dependency and common src files.")
                return True
            else:
                # Still return True if vue dependency found, even without common files
                logger.debug("_check_vue: Found vue dependency in package.json.")
                return True
    except Exception as e:
        logger.warning(f"Could not read or parse package.json for Vue check: {e}")
        
    logger.debug("_check_vue: No clear Vue indicators found.")
    return False

def _check_angular(extracted_path: Path) -> bool:
    """Check for characteristic Angular project files (angular.json)."""
    angular_json_path = extracted_path / "angular.json"
    if angular_json_path.is_file():
        logger.debug("_check_angular: Found angular.json")
        return True
    
    # Optional: Add secondary check for @angular/core in package.json
    # package_json_path = extracted_path / "package.json"
    # if package_json_path.is_file():
    #     try:
    #         pkg_data = read_json_file(package_json_path)
    #         if pkg_data and (
    #             ("dependencies" in pkg_data and "@angular/core" in pkg_data["dependencies"]) or \
    #             ("devDependencies" in pkg_data and "@angular/core" in pkg_data["devDependencies"])
    #         ):
    #             logger.debug("_check_angular: Found @angular/core in package.json")
    #             return True
    #     except Exception as e:
    #         logger.warning(f"Could not read or parse package.json for Angular check: {e}")

    logger.debug("_check_angular: No clear Angular indicators found.")
    return False

def _check_flask(extracted_path: Path) -> bool:
    """Check for Flask files and keywords within Python files."""
    has_flask_file = any((extracted_path / f).is_file() for f in FLASK_FILES)
    if not has_flask_file:
        # Check for keywords in any .py file if common filenames aren't present
        for py_file in extracted_path.rglob('*.py'):
            try:
                content = py_file.read_bytes()
                if any(keyword in content for keyword in FLASK_KEYWORDS):
                    logger.info(f"Detected Flask keyword in {py_file}")
                    return True
            except OSError as e:
                logger.warning(f"Could not read file {py_file} for Flask check: {e}")
        return False
    return True
    

def _check_html(extracted_path: Path) -> bool:
    """Check if an index.html or index.htm file exists at the root."""
    if (extracted_path / "index.html").is_file():
        logger.debug("_check_html: Found index.html")
        return True
    if (extracted_path / "index.htm").is_file(): # Check for .htm as well
        logger.debug("_check_html: Found index.htm")
        return True
    logger.debug("_check_html: No root index file found.")
    return False

# --- Main Detection Logic ---

def detect_framework(extracted_path: Path) -> Tuple[Framework, Engine]:
    """Detects the framework and corresponding engine of the extracted template.

    Checks for specific frameworks first. If none match, checks for a root
    index.html file to classify as HTML. Otherwise, returns UNKNOWN.

    Args:
        extracted_path: Path object pointing to the root of the extracted template content.

    Returns:
        A tuple containing the detected Framework enum member and Engine enum member.
        
    Raises:
        FrameworkDetectionError: If detection fails unexpectedly (not used currently).
        FileNotFoundError: If the extracted_path does not exist.
    """
    if not extracted_path.is_dir():
        raise FileNotFoundError(f"Extracted template path does not exist: {extracted_path}")

    logger.info(f"Starting framework detection in: {extracted_path}")
    final_framework = Framework.UNKNOWN
    final_engine = Engine.STATIC

    # Order checks from most specific/reliable to least specific
    if _check_django(extracted_path):
        logger.info("Detected Framework: Django")
        final_framework, final_engine = Framework.DJANGO, Engine.PYTHON_3_11
        
    elif _check_angular(extracted_path):
        logger.info("Detected Framework: Angular")
        final_framework, final_engine = Framework.ANGULAR, Engine.NODE_18
        
    elif _check_react(extracted_path):
        logger.info("Detected Framework: React")
        final_framework, final_engine = Framework.REACT, Engine.NODE_18
        
    elif _check_vue(extracted_path):
        logger.info("Detected Framework: Vue")
        final_framework, final_engine = Framework.VUE, Engine.NODE_18
        
    elif _check_flask(extracted_path):
        logger.info("Detected Framework: Flask")
        final_framework, final_engine = Framework.FLASK, Engine.PYTHON_3_11
        
    # Check for plain HTML last
    elif _check_html(extracted_path):
        logger.info("Detected Framework: HTML (Static)")
        final_framework, final_engine = Framework.HTML, Engine.STATIC

    # Log final decision (UNKNOWN is the default)
    else:
        logger.warning(f"Could not definitively detect framework in {extracted_path}. Classifying as UNKNOWN.")
        
    logger.info(f"Final detected framework: {final_framework.value}, engine: {final_engine.value}")
    return final_framework, final_engine 