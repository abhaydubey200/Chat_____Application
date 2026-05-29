"""
Metrics and diagnostics hooks for operational monitoring.

Provides:
- Performance metrics tracking
- Provider diagnostics
- Stream lifecycle metrics
- Database operation metrics
"""

from dataclasses import dataclass, asdict
from typing import Optional
from datetime import datetime
from app.core.time import utc_now
from enum import Enum
from threading import Lock


class MetricType(str, Enum):
    """Types of metrics collected."""
    REQUEST_LATENCY = "request_latency"
    FIRST_TOKEN_LATENCY = "first_token_latency"
    STREAM_DURATION = "stream_duration"
    PROVIDER_RESPONSE_TIME = "provider_response_time"
    DB_QUERY_LATENCY = "db_query_latency"
    FAILED_REQUESTS = "failed_requests"
    RETRY_ATTEMPTS = "retry_attempts"
    CONCURRENT_STREAMS = "concurrent_streams"
    PROVIDER_RATE_LIMITS = "provider_rate_limits"
    PROVIDER_TIMEOUTS = "provider_timeouts"
    AUTH_FAILURES = "auth_failures"
    VALIDATION_ERRORS = "validation_errors"


@dataclass
class Metric:
    """Single metric observation."""
    metric_type: MetricType
    value: float
    timestamp: datetime
    tags: dict = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = {}


@dataclass
class MetricsSnapshot:
    """Snapshot of current metrics state."""
    timestamp: datetime
    active_streams: int = 0
    total_requests: int = 0
    failed_requests: int = 0
    total_retries: int = 0
    provider_rate_limits_hit: int = 0
    provider_timeouts: int = 0
    auth_failures: int = 0
    validation_errors: int = 0
    
    # Latency statistics (milliseconds)
    avg_request_latency_ms: Optional[float] = None
    avg_first_token_latency_ms: Optional[float] = None
    avg_stream_duration_ms: Optional[float] = None
    avg_provider_response_time_ms: Optional[float] = None
    
    def to_dict(self) -> dict:
        """Export as dictionary."""
        return asdict(self)


class Metrics:
    """Thread-safe metrics collector for operational monitoring.
    
    Uses a threading.Lock to protect mutable counters from concurrent access
    in async contexts where multiple requests may increment counters simultaneously.
    """
    
    def __init__(self):
        self._lock = Lock()
        self._metrics: list[Metric] = []
        self._active_streams: int = 0
        self._total_requests: int = 0
        self._failed_requests: int = 0
        self._total_retries: int = 0
        self._provider_rate_limits_hit: int = 0
        self._provider_timeouts: int = 0
        self._auth_failures: int = 0
        self._validation_errors: int = 0
    
    def record_metric(self, metric: Metric) -> None:
        """Record a metric observation."""
        with self._lock:
            self._metrics.append(metric)
    
    def increment_active_streams(self, delta: int = 1) -> None:
        """Update active stream count."""
        with self._lock:
            self._active_streams = max(0, self._active_streams + delta)
    
    def increment_total_requests(self) -> None:
        """Increment total request count."""
        with self._lock:
            self._total_requests += 1
    
    def increment_failed_requests(self) -> None:
        """Increment failed request count."""
        with self._lock:
            self._failed_requests += 1
    
    def increment_retries(self) -> None:
        """Increment retry attempt count."""
        with self._lock:
            self._total_retries += 1
    
    def increment_provider_rate_limits(self) -> None:
        """Increment provider rate limit hits."""
        with self._lock:
            self._provider_rate_limits_hit += 1
    
    def increment_provider_timeouts(self) -> None:
        """Increment provider timeout count."""
        with self._lock:
            self._provider_timeouts += 1
    
    def increment_auth_failures(self) -> None:
        """Increment auth failure count."""
        with self._lock:
            self._auth_failures += 1
    
    def increment_validation_errors(self) -> None:
        """Increment validation error count."""
        with self._lock:
            self._validation_errors += 1
    
    def get_snapshot(self) -> MetricsSnapshot:
        """Get current metrics snapshot."""
        with self._lock:
            return MetricsSnapshot(
                timestamp=utc_now(),
                active_streams=self._active_streams,
                total_requests=self._total_requests,
                failed_requests=self._failed_requests,
                total_retries=self._total_retries,
                provider_rate_limits_hit=self._provider_rate_limits_hit,
                provider_timeouts=self._provider_timeouts,
                auth_failures=self._auth_failures,
                validation_errors=self._validation_errors,
            )
    
    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._metrics = []
            self._active_streams = 0
            self._total_requests = 0
            self._failed_requests = 0
            self._total_retries = 0
            self._provider_rate_limits_hit = 0
            self._provider_timeouts = 0
            self._auth_failures = 0
            self._validation_errors = 0


# Global metrics instance
_global_metrics = Metrics()


def get_metrics() -> Metrics:
    """Get the global metrics instance."""
    return _global_metrics
