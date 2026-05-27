"""
Observability and structured logging module for production-grade operational visibility.

Provides:
- Structured JSON logging with correlation IDs
- Request/stream lifecycle tracing
- Error classification and categorization
- Metrics and diagnostics hooks
- Sensitive data redaction
"""

from app.core.observability.structured_logger import (
    get_logger,
    configure_structured_logging,
    StructuredLogger,
)
from app.core.observability.error_types import (
    ProviderTimeoutError,
    ProviderRateLimitError,
    StreamLifecycleError,
    DatabaseConnectionError,
    InvalidAuthError,
    RequestValidationError,
    DushmanError,
)
from app.core.observability.tracing import (
    RequestContext,
    StreamContext,
    get_request_context,
    set_request_context,
    get_stream_context,
    set_stream_context,
    clear_context,
)
from app.core.observability.metrics import (
    Metrics,
    get_metrics,
    MetricsSnapshot,
)

__all__ = [
    "get_logger",
    "configure_structured_logging",
    "StructuredLogger",
    "ProviderTimeoutError",
    "ProviderRateLimitError",
    "StreamLifecycleError",
    "DatabaseConnectionError",
    "InvalidAuthError",
    "RequestValidationError",
    "DushmanError",
    "RequestContext",
    "StreamContext",
    "get_request_context",
    "set_request_context",
    "get_stream_context",
    "set_stream_context",
    "clear_context",
    "Metrics",
    "get_metrics",
    "MetricsSnapshot",
]
