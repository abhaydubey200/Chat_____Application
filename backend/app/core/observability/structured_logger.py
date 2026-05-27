"""
Structured JSON logging for production-grade observability.

Provides:
- JSON-formatted log output with correlation context
- Automatic sensitive data redaction
- Log level management
- Contextual logging with correlation IDs
"""

import json
import logging
import sys
import re
from typing import Optional, Any
from datetime import datetime
from app.core.observability.tracing import get_correlation_dict


class SensitiveDataRedactor:
    """Redacts sensitive data from log messages and context."""
    
    # Patterns for sensitive data
    PATTERNS = {
        'api_key': r'(?:api[_-]?key|apikey|api_secret)["\']?\s*[:=]\s*["\']?([a-zA-Z0-9\-_.]+)["\']?',
        'jwt': r'(?:jwt|token|bearer)["\']?\s*[:=]\s*["\']?([a-zA-Z0-9._\-]+)["\']?',
        'password': r'(?:password|passwd|pwd)["\']?\s*[:=]\s*["\']?([^"\'\s]+)["\']?',
        'auth_header': r'(?:authorization|auth)["\']?\s*[:=]\s*["\']?Bearer\s+([a-zA-Z0-9._\-]+)["\']?',
        'email': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
    }
    
    @staticmethod
    def redact_string(text: str, preserve_type: bool = False) -> str:
        """Redact sensitive data from a string.
        
        Args:
            text: Text to redact
            preserve_type: If True, preserve the data type indicator
            
        Returns:
            Redacted string
        """
        if not isinstance(text, str):
            return text
        
        redacted = text
        for pattern_type, pattern in SensitiveDataRedactor.PATTERNS.items():
            redacted = re.sub(
                pattern,
                f'***{pattern_type}_redacted***',
                redacted,
                flags=re.IGNORECASE
            )
        
        return redacted
    
    @staticmethod
    def redact_dict(data: dict, inplace: bool = False) -> dict:
        """Redact sensitive data from a dictionary.
        
        Args:
            data: Dictionary to redact
            inplace: If True, modify in place; otherwise create a copy
            
        Returns:
            Dictionary with sensitive data redacted
        """
        if not inplace:
            data = data.copy()
        
        sensitive_keys = {
            'password', 'passwd', 'pwd',
            'api_key', 'apikey', 'api_secret', 'secret',
            'token', 'jwt', 'access_token', 'refresh_token',
            'authorization', 'auth',
            'bearer',
            'api_token',
        }
        
        for key in list(data.keys()):
            if key.lower() in sensitive_keys:
                data[key] = '***redacted***'
            elif isinstance(data[key], dict):
                data[key] = SensitiveDataRedactor.redact_dict(data[key], inplace=True)
            elif isinstance(data[key], str):
                data[key] = SensitiveDataRedactor.redact_string(data[key])
        
        return data


class StructuredFormatter(logging.Formatter):
    """Formats logs as JSON with correlation context and structured fields."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as JSON.
        
        Args:
            record: LogRecord to format
            
        Returns:
            JSON-formatted log string
        """
        log_obj = {
            'timestamp': datetime.utcfromtimestamp(record.created).isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }
        
        # Add correlation context
        correlation = get_correlation_dict()
        log_obj.update(correlation)
        
        # Add extra fields from record
        if hasattr(record, '__dict__'):
            for key, value in record.__dict__.items():
                # Skip standard LogRecord attributes
                if key not in {
                    'name', 'msg', 'args', 'created', 'filename',
                    'funcName', 'levelname', 'levelno', 'lineno',
                    'module', 'msecs', 'pathname', 'process',
                    'processName', 'relativeCreated', 'thread',
                    'threadName', 'exc_info', 'exc_text', 'stack_info',
                    'getMessage', 'message', 'asctime',
                }:
                    log_obj[key] = value
        
        # Add exception info if present
        if record.exc_info:
            exc_type, exc_value, exc_tb = record.exc_info
            log_obj['exception'] = {
                'type': exc_type.__name__,
                'message': str(exc_value),
                'traceback': self.formatException(record.exc_info),
            }
        
        # Redact sensitive data
        log_obj = SensitiveDataRedactor.redact_dict(log_obj)
        
        return json.dumps(log_obj, default=str)


class StructuredLogger(logging.Logger):
    """Extended logger with structured logging methods."""
    
    def log_request_start(
        self,
        method: str,
        path: str,
        client_ip: str,
        user_id: Optional[str] = None,
        **extra,
    ) -> None:
        """Log the start of an HTTP request.
        
        Args:
            method: HTTP method
            path: Request path
            client_ip: Client IP address
            user_id: Authenticated user ID (if available)
            **extra: Additional context fields
        """
        self.info(
            f"HTTP request started: {method} {path}",
            extra={
                'event_type': 'request_start',
                'http_method': method,
                'http_path': path,
                'client_ip': client_ip,
                'user_id': user_id,
                **extra,
            }
        )
    
    def log_request_end(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        **extra,
    ) -> None:
        """Log the end of an HTTP request.
        
        Args:
            method: HTTP method
            path: Request path
            status_code: HTTP response status code
            duration_ms: Request duration in milliseconds
            **extra: Additional context fields
        """
        level = logging.INFO if 200 <= status_code < 400 else logging.WARNING
        self.log(
            level,
            f"HTTP request completed: {method} {path} {status_code} ({duration_ms:.2f}ms)",
            extra={
                'event_type': 'request_end',
                'http_method': method,
                'http_path': path,
                'http_status': status_code,
                'duration_ms': duration_ms,
                **extra,
            }
        )
    
    def log_stream_start(
        self,
        stream_id: str,
        model_type: str,
        provider_name: str,
        **extra,
    ) -> None:
        """Log the start of a streaming response.
        
        Args:
            stream_id: Unique stream identifier
            model_type: Model type being used
            provider_name: Provider name
            **extra: Additional context fields
        """
        self.info(
            f"Stream started: {provider_name} ({model_type})",
            extra={
                'event_type': 'stream_start',
                'stream_id': stream_id,
                'model_type': model_type,
                'provider': provider_name,
                **extra,
            }
        )
    
    def log_stream_end(
        self,
        stream_id: str,
        completion_reason: str,
        duration_ms: float,
        tokens_generated: int = 0,
        **extra,
    ) -> None:
        """Log the end of a streaming response.
        
        Args:
            stream_id: Unique stream identifier
            completion_reason: How stream completed (completed, cancelled, error, timeout)
            duration_ms: Stream duration in milliseconds
            tokens_generated: Number of tokens generated
            **extra: Additional context fields
        """
        level = logging.INFO if completion_reason == "completed" else logging.WARNING
        self.log(
            level,
            f"Stream ended: {completion_reason} ({duration_ms:.2f}ms, {tokens_generated} tokens)",
            extra={
                'event_type': 'stream_end',
                'stream_id': stream_id,
                'completion_reason': completion_reason,
                'duration_ms': duration_ms,
                'tokens_generated': tokens_generated,
                **extra,
            }
        )
    
    def log_provider_request(
        self,
        provider_name: str,
        model_name: str,
        message_count: int,
        **extra,
    ) -> None:
        """Log a request to an LLM provider.
        
        Args:
            provider_name: Provider name
            model_name: Model being used
            message_count: Number of messages in conversation
            **extra: Additional context fields
        """
        self.debug(
            f"Provider request: {provider_name}/{model_name} ({message_count} messages)",
            extra={
                'event_type': 'provider_request',
                'provider': provider_name,
                'model': model_name,
                'message_count': message_count,
                **extra,
            }
        )
    
    def log_provider_response(
        self,
        provider_name: str,
        model_name: str,
        latency_ms: float,
        status: str = "success",
        **extra,
    ) -> None:
        """Log a response from an LLM provider.
        
        Args:
            provider_name: Provider name
            model_name: Model being used
            latency_ms: Response latency in milliseconds
            status: Response status (success, timeout, rate_limit, error)
            **extra: Additional context fields
        """
        level = logging.INFO if status == "success" else logging.WARNING
        self.log(
            level,
            f"Provider response: {provider_name}/{model_name} ({status}, {latency_ms:.2f}ms)",
            extra={
                'event_type': 'provider_response',
                'provider': provider_name,
                'model': model_name,
                'latency_ms': latency_ms,
                'status': status,
                **extra,
            }
        )
    
    def log_db_query(
        self,
        operation: str,
        table: str,
        duration_ms: float,
        rows_affected: int = 0,
        **extra,
    ) -> None:
        """Log a database operation.
        
        Args:
            operation: SQL operation (SELECT, INSERT, UPDATE, DELETE)
            table: Table being accessed
            duration_ms: Query duration in milliseconds
            rows_affected: Number of rows affected
            **extra: Additional context fields
        """
        self.debug(
            f"DB {operation}: {table} ({duration_ms:.2f}ms, {rows_affected} rows)",
            extra={
                'event_type': 'db_query',
                'operation': operation,
                'table': table,
                'duration_ms': duration_ms,
                'rows_affected': rows_affected,
                **extra,
            }
        )
    
    def log_auth_event(
        self,
        event_type: str,
        user_id: Optional[str] = None,
        status: str = "success",
        **extra,
    ) -> None:
        """Log an authentication event.
        
        Args:
            event_type: Event type (login, logout, signup, token_refresh)
            user_id: User ID (if applicable)
            status: Event status (success, failure)
            **extra: Additional context fields
        """
        level = logging.INFO if status == "success" else logging.WARNING
        self.log(
            level,
            f"Auth event: {event_type} ({status})",
            extra={
                'event_type': f'auth_{event_type}',
                'user_id': user_id,
                'status': status,
                **extra,
            }
        )


def configure_structured_logging(
    level: int = logging.INFO,
    use_json: bool = True,
) -> None:
    """Configure structured logging for the application.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        use_json: If True, format logs as JSON; otherwise use text format
    """
    # Set custom logger class
    logging.setLoggerClass(StructuredLogger)
    
    # Remove existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    # Set formatter
    if use_json:
        formatter = StructuredFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] [%(name)s] %(message)s'
        )
    
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger.setLevel(level)
    root_logger.addHandler(console_handler)


def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        StructuredLogger instance
    """
    logger = logging.getLogger(name)
    if not isinstance(logger, StructuredLogger):
        logging.setLoggerClass(StructuredLogger)
        logger = logging.getLogger(name)
    return logger
