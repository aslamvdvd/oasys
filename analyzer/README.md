# OASYS Template Analyzer (`analyzer` app)

## 1. Purpose

The `analyzer` app serves as an internal service within the OASYS platform responsible for processing uploaded template ZIP archives. Its primary functions are:

*   **Validation:** Performs structural checks on the extracted template content.
*   **Framework Detection:** Attempts to identify the web framework (e.g., Django, React, HTML) used by the template.
*   **Metadata Generation:** Creates or validates a `metadata.json` file containing essential template information.
*   **Configuration Generation:** Creates an `engine_config.json` file required by the template rendering/serving engine, detailing runtime, entry points, static directories, and dependencies.

This service is **not user-facing** and has no associated URLs. It is designed to be invoked internally, typically after a template ZIP file associated with the `templator.Template` model has been extracted.

## 2. Workflow

The typical workflow involving the analyzer is:

1.  A user uploads a ZIP archive via the `templator` app (e.g., through the Django Admin).
2.  The `templator` app saves the `Template` model instance.
3.  A `post_save` signal handler (in `templator.signals`) is triggered.
4.  The signal handler calls a utility function (e.g., `templator.utils.process_template_upload`) to extract the ZIP archive to a designated location (usually within `settings.TEMPLATE_UPLOAD_PATH`).
5.  The signal handler then calls the `analyzer.validator.validate_template` function, passing the path to the extracted directory and optional metadata from the `Template` model instance.
6.  The `validate_template` function orchestrates the analysis:
    *   Performs basic structural checks (e.g., presence of common directories).
    *   Processes `metadata.json`: Loads and validates if it exists, otherwise generates a default version.
    *   Detects the framework using `analyzer.framework_detector.detect_framework` if not specified or invalid in metadata.
    *   Updates the `metadata.json` file if necessary (e.g., adding the detected framework).
    *   Detects dependencies (`requirements.txt`, `package.json`) based on the detected framework/engine.
    *   Generates `engine_config.json` with details like entry point, static directory, runtime, dependencies, and framework.
7.  The `validate_template` function returns a dictionary containing the status (`success` or `error`), detected framework, paths to generated files, and lists of any warnings or errors encountered.
8.  The calling signal handler (in `templator.signals`) receives the results, updates the `Template` model instance (e.g., saving the `detected_framework`), and logs relevant information.

## 3. Key Components

*   **`validator.py`:** Contains the main `TemplateValidator` class and the public `validate_template` function. Orchestrates the entire analysis process.
*   **`framework_detector.py`:** Implements the logic (`detect_framework` and helper functions like `_check_django`, `_check_react`, etc.) to identify the template's framework based on file/directory patterns and content heuristics.
*   **`utils.py`:** Provides helper functions for safe file I/O (`read_json_file`, `write_json_file`), JSON schema validation (`validate_json_schema`), dependency parsing (`parse_requirements_txt`, `parse_package_json`), and potentially safe ZIP extraction (though extraction might currently be handled by `templator.utils`).
*   **`constants.py`:** Defines shared constants, primarily Enums for `Framework` and `Engine`, standard filenames (`METADATA_FILENAME`, etc.), and status strings.
*   **`exceptions.py`:** Defines custom exception classes (`AnalyzerError`, `InvalidTemplateError`, `MetadataError`, `SchemaValidationError`, `FileOperationError`) for structured error handling.
*   **`schemas/`:** Contains JSON schema definitions (`metadata_schema.json`, `engine_config_schema.json`) used for validating the generated configuration files.
*   **`apps.py`:** Standard Django app configuration.
*   **`signals.py`:** (Optional) Placeholder for potential future signals emitted *by* the analyzer (e.g., `analysis_completed`).
*   **`tests/`:** Contains unit tests (using pytest conventions) for the different components.

## 4. Generated Files

The analyzer creates/updates the following files within the root of the extracted template directory:

*   **`metadata.json`:** Contains essential information about the template.
    *   `name`: Human-readable name.
    *   `slug`: Unique slug (matches the `Template` model slug).
    *   `framework`: The detected or specified framework (e.g., `django`, `react`, `html`).
    *   `category`: The slug of the template's category.
    *   `author`: Username of the uploader.
    *   `version`: Template version (currently defaults to "1.0").
*   **`engine_config.json`:** Provides configuration details for the rendering/serving engine.
    *   `entry_point`: Path to the primary file needed to run/serve the template (e.g., `index.html`, `wsgi.py`, `app.py`). Meaning depends on the framework.
    *   `static_dir`: Relative path to the primary directory containing static assets (e.g., `assets`, `static`, `public`).
    *   `runtime`: Required runtime environment (e.g., `python3.11`, `nodejs18`, `html`).
    *   `dependencies`: List of detected package dependencies (e.g., from `requirements.txt` or `package.json`).
    *   `framework`: The detected framework (should match `metadata.json`).
    *   `author`: Username of the uploader (optional).

## 5. Integration & Usage

This app is intended for internal use only. The primary way to interact with it is by importing and calling the `validate_template` function:

```python
from analyzer.validator import validate_template
from pathlib import Path

# Assuming 'template_instance' is an instance of templator.Template
# and 'extraction_dir_path' is the Path object where the zip was extracted
extraction_dir_path = Path("/path/to/extracted/template/content")

# Optional: Prepare info from the model
template_info = {
    'name': template_instance.name,
    'slug': template_instance.slug,
    'category_slug': template_instance.category.slug if template_instance.category else 'uncategorized',
    'author_username': template_instance.uploaded_by.username if template_instance.uploaded_by else 'unknown',
    'version': '1.0' # Or fetch from model if added
}

# Call the analyzer
analysis_results = validate_template(extraction_dir_path, template_info)

# Process results
if analysis_results['status'] == 'success':
    detected_framework = analysis_results['framework']
    # Update Template model, log success, etc.
    print(f"Analysis successful. Detected framework: {detected_framework}")
    # template_instance.detected_framework = detected_framework
    # template_instance.save(update_fields=['detected_framework'])
else:
    # Log errors/warnings
    print(f"Analysis failed. Errors: {analysis_results['errors']}")
    for warning in analysis_results['warnings']:
        print(f"Warning: {warning}")
```

## 6. Framework Support

### Currently Supported:

The analyzer attempts to detect and configure the following frameworks:

*   Django
*   Flask
*   React
*   Angular
*   Vue.js
*   HTML (Basic static sites)

Detection is based on common file/directory structures and presence of specific configuration files (`package.json`, `angular.json`, etc.) or keywords.

### Planned Future Support:

These frameworks are **not yet** explicitly supported by the analyzer's detection and specific configuration logic, but support is planned or desirable for future versions:

*   **🌐 Front-end Frameworks**
    *   Next.js
    *   Nuxt.js (Vue SSR)
    *   Svelte
    *   SvelteKit
    *   Astro
    *   Alpine.js
    *   Ember.js
    *   Preact
*   **🖥️ Backend Frameworks**
    *   FastAPI
    *   Express.js (Node.js)
    *   Laravel (PHP)
    *   Ruby on Rails
    *   Spring Boot (Java)
    *   ASP.NET Core
*   **⚙️ Full-Stack / Meta-Frameworks**
    *   Remix (React-based)
    *   Blitz.js (full-stack React)
    *   RedwoodJS (JAMstack, GraphQL)
    *   Meteor.js
    *   Quasar (Vue-based full-stack)

*(Templates using unsupported frameworks might be detected as UNKNOWN or misclassified as HTML/basic JS)*

## 7. Security Considerations

*   The calling process (e.g., `templator`) should handle initial ZIP validation (e.g., size limits, basic format check).
*   Utilities within the analyzer (`utils.py`) should perform safe extraction, preventing path traversal attacks and potentially checking for zip bombs.
*   JSON parsing and schema validation help mitigate risks from malformed configuration files if they were included in the upload (currently, the analyzer generates them). 