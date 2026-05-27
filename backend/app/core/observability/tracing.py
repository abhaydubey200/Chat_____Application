"""
Request and stream context tracing for distributed tracing and correlation.

Provides:
- Request context management (request_id, user_id, etc.)
- Stream context management (stream_id, lifecycle events)
- Context locals for async-safe propagation
"""

import uuid
from contextvars import ContextVar
from dataclasses import dataclass, asdict, field
from typing import Optional
from datetime import datetime


@dataclass
class RequestContext:
    """Correlation context for a single HTTP request."""
    
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    organization_id: Optional[str] = None
    role: Optional[str] = None
    conversation_id: Optional[str] = None
    http_method: str = ""
    http_path: str = ""
    http_status: Optional[int] = None
    client_ip: str = ""
    user_agent: str = ""
    
    # Timing
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    # Request/response sizes (bytes)
    request_size_bytes: Optional[int] = None
    response_size_bytes: Optional[int] = None
    
    def to_dict(self) -> dict:
        """Export context as dictionary for logging."""
        data = asdict(self)
        # Convert datetime to ISO strings for JSON serialization
        if self.start_time:
            data['start_time'] = self.start_time.isoformat()
        if self.end_time:
            data['end_time'] = self.end_time.isoformat()
        return data
    
    def duration_ms(self) -> Optional[float]:
        """Calculate request duration in milliseconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds() * 1000
        return None


@dataclass
class StreamContext:
    """Correlation context for a streaming response (SSE)."""
    
    stream_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    request_id: str = ""  # Reference to parent request
    user_id: Optional[str] = None
    conversation_id: Optional[str] = None
    model_type: str = ""
    provider_name: str = ""
    model_name: str = ""
    
    # Stream lifecycle
    stream_start_time: Optional[datetime] = None
    first_token_time: Optional[datetime] = None
    stream_end_time: Optional[datetime] = None
    
    # Stream statistics
    chunk_count: int = 0
    total_tokens: int = 0
    retry_count: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    stream_error: Optional[str] = None
    completion_reason: str = ""  # "completed", "cancelled", "error", "timeout"
    
    # Provider statistics
    provider_latency_ms: Optional[float] = None
    provider_request_time: Optional[datetime] = None
    provider_response_time: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """Export context as dictionary for logging."""
        data = asdict(self)
        # Convert datetime to ISO strings for JSON serialization
        for key in ['stream_start_time', 'first_token_time', 'stream_end_time', 
                   'provider_request_time', 'provider_response_time']:
            if data[key]:
                data[key] = data[key].isoformat()
        return data
    
    def stream_duration_ms(self) -> Optional[float]:
        """Calculate stream duration in milliseconds."""
        if self.stream_start_time and self.stream_end_time:
            return (self.stream_end_time - self.stream_start_time).total_seconds() * 1000
        return None
    
    def first_token_latency_ms(self) -> Optional[float]:
        """Calculate latency to first token in milliseconds."""
        if self.stream_start_time and self.first_token_time:
            return (self.first_token_time - self.stream_start_time).total_seconds() * 1000
        return None


# Global context variables for async-safe storage
_request_context: ContextVar[Optional[RequestContext]] = ContextVar(
    'request_context', default=None
)
_stream_context: ContextVar[Optional[StreamContext]] = ContextVar(
    'stream_context', default=None
)


def get_request_context() -> Optional[RequestContext]:
    """Get the current request context."""
    return _request_context.get()


def set_request_context(context: RequestContext) -> None:
    """Set the current request context."""
    _request_context.set(context)


def get_stream_context() -> Optional[StreamContext]:
    """Get the current stream context."""
    return _stream_context.get()


def set_stream_context(context: StreamContext) -> None:
    """Set the current stream context."""
    _stream_context.set(context)


def clear_context() -> None:
    """Clear all context variables."""
    _request_context.set(None)
    _stream_context.set(None)


def get_correlation_dict() -> dict:
    """Get a dictionary of all active correlation IDs for logging.
    
    Returns a dict containing:
    - request_id
    - stream_id (if in stream context)
    - user_id
    - conversation_id
    
    Safe for concurrent requests and async contexts.
    """
    req_ctx = get_request_context()
    stream_ctx = get_stream_context()
    
    correlation = {}
    
    if req_ctx:
        correlation['request_id'] = req_ctx.request_id
        if req_ctx.user_id:
            correlation['user_id'] = req_ctx.user_id
        if req_ctx.session_id:
            correlation['session_id'] = req_ctx.session_id
        if req_ctx.organization_id:
            correlation['organization_id'] = req_ctx.organization_id
        if req_ctx.role:
            correlation['role'] = req_ctx.role
        if req_ctx.conversation_id:
            correlation['conversation_id'] = req_ctx.conversation_id
    
    if stream_ctx:
        correlation['stream_id'] = stream_ctx.stream_id
        if stream_ctx.user_id and not correlation.get('user_id'):
            correlation['user_id'] = stream_ctx.user_id
        if stream_ctx.conversation_id and not correlation.get('conversation_id'):
            correlation['conversation_id'] = stream_ctx.conversation_id
    
    return correlation
