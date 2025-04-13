# Templator App

A Django app for managing template uploads and organization for the OASYS platform.

## Purpose

The Templator app allows administrators to upload ZIP files containing templates (HTML, CSS, JS, etc.) that can be used throughout the OASYS platform. Templates are categorized and stored in a structured file system.

## Features

- Template categories for organization
- ZIP file upload and automatic extraction
- Structured storage based on category/template hierarchy
- Admin interface for template management
- Integration with log_service for activity logging
- Preview image support for templates
- Automatic cleanup when templates are deleted

## Directory Structure

When a template ZIP is uploaded and extracted, it follows this structure:

```
templates_store/
  └── <category_slug>/
       └── <template_slug>/
             ├── static/      (contains CSS, JS, images, etc.)
             ├── templates/   (contains HTML files)
             └── config.json  (optional metadata)
```

## Models

### TemplateCategory

- `name`: Name of the category
- `slug`: URL-friendly slug (auto-generated if not provided)
- `description`: Optional description of the category

### Template

- `name`: Name of the template
- `slug`: URL-friendly slug (auto-generated if not provided)
- `description`: Optional description of the template
- `category`: Foreign key to TemplateCategory
- `zip_file`: Uploaded ZIP file containing the template
- `date_uploaded`: Date and time of upload
- `is_active`: Boolean flag to enable/disable the template
- `preview_image`: Optional preview image for the template
- `uploaded_by`: User who uploaded the template
- `extraction_path`: Path where the template files were extracted

## Workflow

1. Admin creates a template category
2. Admin uploads a template ZIP file (must contain 'static' and 'templates' folders)
3. The system validates the ZIP file contents
4. If valid, the ZIP is extracted to the appropriate directory
5. The extraction path is stored in the Template object
6. The template can now be used throughout the OASYS platform

## Logging

The templator app logs all important activities to help with debugging and auditing. Two types of logs are maintained:

1. **Templator Logs**: All template-related operations (uploads, extractions, deletions) are logged to `templator.log` in the date-based directory structure (`logs/YYYY-MM-DD/templator.log`). This provides detailed information about template management operations.

2. **Admin Logs**: Admin actions (creating/updating/deleting templates and categories) are logged to `admin.log` in the same date-based directory structure (`logs/YYYY-MM-DD/admin.log`). This provides an audit trail of all administrative actions.

The logs are structured as JSON for easy parsing and include:

- Timestamp of the event
- User who performed the action
- Action type
- Details of the affected objects
- Any error messages (if applicable)

## Error Handling

- ZIP validation ensures required folders exist
- Directory creation uses Path.mkdir(parents=True, exist_ok=True)
- All file operations are wrapped in try/except blocks
- Errors are logged using log_service to both templator.log and failures.log
- Partially extracted files are cleaned up if an error occurs

## Future Extensions

This app is designed to be modular and extensible. Possible future enhancements:

- User-facing dashboard for template management
- Template versioning
- Template previews
- Template import/export
- Template sharing and permissions
- Template usage analytics 

templator/
├── __init__.py
├── admin.py               # Admin interface customization
├── apps.py                # App configuration with signal connection
├── migrations/            # Database migrations
│   └── 0001_initial.py    # Initial migration
├── models.py              # Template and TemplateCategory models
├── README.md              # App documentation
├── signals.py             # Signal handlers for template processing
├── tests.py               # (Empty) Test file
├── utils.py               # Utility functions for ZIP handling
└── views.py               # (Empty) Views file 