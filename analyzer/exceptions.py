# Custom exceptions for the analyzer app

class AnalyzerError(Exception):
    """Base exception class for analyzer errors."""
    pass

class InvalidTemplateError(AnalyzerError):
    """Raised when the template structure or content is invalid."""
    def __init__(self, message="Invalid template structure or content", details=None):
        super().__init__(message)
        self.details = details or []

class MetadataError(InvalidTemplateError):
    """Raised for issues related to metadata.json."""
    def __init__(self, message="Error processing metadata file", details=None):
        super().__init__(message, details)

class FrameworkDetectionError(AnalyzerError):
    """Raised when framework detection fails or is ambiguous."""
    pass

class SchemaValidationError(InvalidTemplateError):
    """Raised when JSON data fails schema validation."""
    def __init__(self, message="Schema validation failed", errors=None):
        super().__init__(message)
        self.errors = errors or []

class FileOperationError(AnalyzerError):
    """Raised for errors during file I/O operations."""
    pass
 