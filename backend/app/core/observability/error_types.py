"""
Error classification system for Dushman AI.

Provides normalized error categories for consistent error handling, logging, and diagnostics.
"""

from typing import Optional
from enum import Enum


class ErrorCategory(str, Enum):
    """Normalized error categories for classification."""
    PROVIDER_TIMEOUT = "provider_timeout"
    PROVIDER_RATE_LIMIT = "provider_rate_limit"
    PROVIDER_ERROR = "provider_error"
    STREAM_LIFECYCLE = "stream_lifecycle"
    DATABASE_CONNECTION = "database_connection"
    DATABASE_INTEGRITY = "database_integrity"
    INVALID_AUTH = "invalid_auth"
    REQUEST_VALIDATION = "request_validation"
    CONFIGURATION = "configuration"
    UNKNOWN = "unknown"


class DushmanError(Exception):
    """Base exception class for Dushman AI with observability context."""
    
    category: ErrorCategory = ErrorCategory.UNKNOWN
    
    def __init__(
        self,
        message: str,
        category: Optional[ErrorCategory] = None,
        context: Optional[dict] = None,
        original_error: Optional[Exception] = None,
    ):
        """Initialize Dushman error with context for observability.
        
        Args:
            message: Human-readable error message
            category: Error category for classification
            context: Additional context dict (never expose sensitive data)
            original_error: Original exception that triggered this error
        """
        super().__init__(message)
        self.message = message
        if category:
            self.category = category
        self.context = context or {}
        self.original_error = original_error


class ProviderTimeoutError(DushmanError):
    """Provider did not respond within timeout window."""
    category = ErrorCategory.PROVIDER_TIMEOUT


class ProviderRateLimitError(DushmanError):
    """Provider returned rate limit error (429)."""
    category = ErrorCategory.PROVIDER_RATE_LIMIT


class ProviderError(DushmanError):
    """Generic provider-side error."""
    category = ErrorCategory.PROVIDER_ERROR


class StreamLifecycleError(DushmanError):
    """Error during stream lifecycle (e.g., premature termination, data corruption)."""
    category = ErrorCategory.STREAM_LIFECYCLE


class DatabaseConnectionError(DushmanError):
    """Cannot establish or maintain database connection."""
    category = ErrorCategory.DATABASE_CONNECTION


class DatabaseIntegrityError(DushmanError):
    """Database constraint or data integrity violation."""
    category = ErrorCategory.DATABASE_INTEGRITY


class InvalidAuthError(DushmanError):
    """Authentication or authorization failure."""
    category = ErrorCategory.INVALID_AUTH


class RequestValidationError(DushmanError):
    """Request payload validation failure."""
    category = ErrorCategory.REQUEST_VALIDATION


class ConfigurationError(DushmanError):
    """Configuration or initialization failure."""
    category = ErrorCategory.CONFIGURATION


def get_error_category(exc: Exception) -> ErrorCategory:
    """Classify an exception into a normalized error category.
    
    Args:
        exc: Exception to classify
        
    Returns:
        ErrorCategory for the exception
    """
    if isinstance(exc, DushmanError):
        return exc.category
    
    exc_type_name = type(exc).__name__.lower()
    exc_str = str(exc).lower()
    
    # Timeout detection
    if "timeout" in exc_type_name or "timeout" in exc_str:
        return ErrorCategory.PROVIDER_TIMEOUT
    
    # Rate limit detection
    if "rate" in exc_type_name or "429" in exc_str or "rate limit" in exc_str:
        return ErrorCategory.PROVIDER_RATE_LIMIT
    
    # Database connection detection
    if "connection" in exc_type_name or "database" in exc_type_name:
        return ErrorCategory.DATABASE_CONNECTION
    
    # Database integrity detection
    if "integrity" in exc_type_name or "constraint" in exc_type_name:
        return ErrorCategory.DATABASE_INTEGRITY
    
    # Auth detection
    if "auth" in exc_type_name or "permission" in exc_type_name or "unauthorized" in exc_str:
        return ErrorCategory.INVALID_AUTH
    
    # Validation detection
    if "validation" in exc_type_name or "pydantic" in exc_type_name:
        return ErrorCategory.REQUEST_VALIDATION
    
    return ErrorCategory.UNKNOWN
