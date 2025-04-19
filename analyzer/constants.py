# Constants for the analyzer app (e.g., Frameworks, Engines) 

import enum

class Framework(enum.Enum):
    """Supported template frameworks."""
    DJANGO = "django"
    FLASK = "flask"
    REACT = "react"
    ANGULAR = "angular"
    VUE = "vue"
    HTML = "html"  # Plain HTML/CSS/JS
    UNKNOWN = "unknown"

class Engine(enum.Enum):
    """Supported rendering engines or runtimes."""
    PYTHON_3_11 = "python3.11"
    NODE_18 = "nodejs18"
    STATIC = "html" # For plain HTML/CSS/JS
    # Add more as needed

# --- File/Directory Names ---
METADATA_FILENAME = "metadata.json"
ENGINE_CONFIG_FILENAME = "engine_config.json"
TEMPLATE_DIR_NAME = "templates"
STATIC_DIR_NAME = "static"

# --- Schema Paths (Relative to this app) ---
# Consider making this configurable via settings or env vars if needed
SCHEMA_DIR = "schemas"
METADATA_SCHEMA_FILE = f"{SCHEMA_DIR}/metadata_schema.json"
ENGINE_CONFIG_SCHEMA_FILE = f"{SCHEMA_DIR}/engine_config_schema.json"

# --- Status ---
STATUS_SUCCESS = "success"
STATUS_ERROR = "error" 