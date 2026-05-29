import logging
import asyncio
import time
from datetime import datetime, timezone
from typing import AsyncGenerator
from app.core.config import settings
from app.providers.registry import provider_registry
from app.core.observability import get_logger, get_stream_context, get_metrics
from app.core.observability.metrics import Metric, MetricType

logger = get_logger(__name__)


class CircuitBreakerState:
    """Tracks circuit breaker state per provider for failover logic."""
    
    def __init__(self, failure_threshold: int = 3, reset_timeout: float = 30.0):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.last_failure_time = 0.0
        self.is_open = False

    def record_success(self) -> None:
        self.failure_count = 0
        self.is_open = False

    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.is_open = True
            logger.warning(
                f"Circuit breaker opened for provider after {self.failure_count} failures",
                extra={"event_type": "circuit_breaker_opened", "failure_count": self.failure_count},
            )

    def attempt_reset(self) -> bool:
        if self.is_open and (time.time() - self.last_failure_time) > self.reset_timeout:
            logger.info(
                "Circuit breaker reset timeout elapsed, attempting reset",
                extra={"event_type": "circuit_breaker_reset"},
            )
            self.is_open = False
            self.failure_count = 0
            return True
        return False


# Global circuit breaker instances per provider
_circuit_breakers: dict[str, CircuitBreakerState] = {}


def _get_circuit_breaker(name: str) -> CircuitBreakerState:
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreakerState()
    return _circuit_breakers[name]


# Ordered list of providers to try as fallback
FALLBACK_PROVIDERS = ["nvidia", "gemini"]


class LLMRouter:
    @property
    def provider_name(self) -> str:
        """Get the active provider name from environment configuration."""
        return settings.LLM_PROVIDER

    def resolve_model(self, model_type: str) -> str:
        """Map abstract model types to concrete model identifiers based on active provider."""
        provider = self.provider_name.lower()
        
        if provider == "nvidia":
            if model_type == "fast":
                return settings.NVIDIA_MODEL_FAST
            elif model_type == "reasoning":
                return settings.NVIDIA_MODEL_REASONING
            return settings.NVIDIA_MODEL_DEFAULT
            
        elif provider == "gemini":
            if model_type == "fast":
                return settings.GEMINI_MODEL_FAST
            elif model_type == "reasoning":
                return settings.GEMINI_MODEL_REASONING
            return settings.GEMINI_MODEL_DEFAULT
            
        # Fallback to direct model name matching if custom name is passed
        return model_type

    def _resolve_model_for_provider(self, provider_name: str, model_type: str) -> str:
        """Resolve model name for a specific provider (used for fallback)."""
        if provider_name == "nvidia":
            if model_type == "fast":
                return settings.NVIDIA_MODEL_FAST
            elif model_type == "reasoning":
                return settings.NVIDIA_MODEL_REASONING
            return settings.NVIDIA_MODEL_DEFAULT
        elif provider_name == "gemini":
            if model_type == "fast":
                return settings.GEMINI_MODEL_FAST
            elif model_type == "reasoning":
                return settings.GEMINI_MODEL_REASONING
            return settings.GEMINI_MODEL_DEFAULT
        return model_type

    async def _stream_from_provider(
        self,
        provider_name: str,
        resolved_model: str,
        messages: list[dict],
        model_type: str,
    ) -> AsyncGenerator[dict, None]:
        """Stream from a specific provider with circuit breaker awareness."""
        circuit_breaker = _get_circuit_breaker(provider_name)

        # Check circuit breaker
        if circuit_breaker.is_open:
            if not circuit_breaker.attempt_reset():
                logger.warning(
                    f"Circuit breaker is open for provider '{provider_name}', skipping",
                    extra={
                        "event_type": "circuit_breaker_skip",
                        "provider": provider_name,
                    },
                )
                yield {
                    "type": "error",
                    "content": f"Provider '{provider_name}' is temporarily unavailable (circuit breaker open).",
                }
                return

        try:
            provider = provider_registry.get_provider(provider_name)
        except Exception as e:
            circuit_breaker.record_failure()
            yield {
                "type": "error",
                "content": f"Failed to load provider '{provider_name}': {str(e)}",
            }
            return

        stream_ctx = get_stream_context()
        if stream_ctx:
            stream_ctx.provider_name = provider_name
            stream_ctx.model_name = resolved_model

        metrics = get_metrics()
        had_content = False

        try:
            async for chunk in provider.stream_chat(messages, resolved_model):
                if chunk["type"] in ("delta", "done"):
                    chunk["provider"] = provider_name
                    chunk["model"] = resolved_model
                if chunk["type"] == "delta":
                    had_content = True
                yield chunk

            if had_content:
                circuit_breaker.record_success()
                metrics.record_metric(
                    Metric(
                        metric_type=MetricType.PROVIDER_RESPONSE_TIME,
                        value=0,
                        timestamp=datetime.now(timezone.utc),
                        tags={"provider": provider_name, "status": "success"},
                    )
                )
            else:
                # No content is considered a failure for circuit breaker purposes
                circuit_breaker.record_failure()

        except Exception as e:
            circuit_breaker.record_failure()
            metrics.increment_provider_timeouts()
            logger.error(
                f"Provider streaming failed for '{provider_name}': {e}",
                extra={
                    "event_type": "provider_stream_error",
                    "provider": provider_name,
                    "model": resolved_model,
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            yield {
                "type": "error",
                "content": f"Provider '{provider_name}' error: {str(e)[:100]}",
            }

    def _get_fallback_chain(self) -> list[str]:
        """Get ordered list of providers to try, starting with primary."""
        primary = self.provider_name.lower()
        
        # Build ordered chain: primary first, then all others
        chain = [primary]
        for p in FALLBACK_PROVIDERS:
            if p != primary:
                # Only include if API key is configured
                if p == "nvidia" and settings.NVIDIA_API_KEY:
                    chain.append(p)
                elif p == "gemini" and settings.GEMINI_API_KEY:
                    chain.append(p)
        return chain

    async def stream(self, messages: list[dict], model_type: str) -> AsyncGenerator[dict, None]:
        """Route message stream to the configured LLM provider with automatic failover.
        
        If the primary provider fails, falls back to the next available provider.
        Includes circuit breaker pattern to avoid hammering failing providers.
        Includes comprehensive observability for provider selection and routing.
        """
        provider_chain = self._get_fallback_chain()
        stream_ctx = get_stream_context()
        last_error = None

        logger.debug(
            "Routing streaming request with failover chain",
            extra={
                "event_type": "routing_request",
                "provider_chain": provider_chain,
                "model_type": model_type,
                "message_count": len(messages),
            },
        )

        for attempt_index, provider_name in enumerate(provider_chain):
            resolved_model = self._resolve_model_for_provider(provider_name, model_type)

            logger.debug(
                f"Attempting provider: {provider_name} (attempt {attempt_index + 1}/{len(provider_chain)})",
                extra={
                    "event_type": "routing_attempt",
                    "provider": provider_name,
                    "model": resolved_model,
                    "attempt": attempt_index + 1,
                    "total_attempts": len(provider_chain),
                },
            )

            if stream_ctx and attempt_index > 0:
                stream_ctx.retry_count = attempt_index

            # Stream from this provider
            had_error_from_provider = False
            accumulated = []

            async for chunk in self._stream_from_provider(
                provider_name, resolved_model, messages, model_type
            ):
                if chunk["type"] == "error":
                    had_error_from_provider = True
                    last_error = chunk["content"]
                    logger.warning(
                        f"Provider '{provider_name}' returned error, will try fallback",
                        extra={
                            "event_type": "provider_fallback",
                            "failed_provider": provider_name,
                            "fallback_attempt": attempt_index + 1,
                            "error": chunk["content"],
                        },
                    )
                    break
                else:
                    accumulated.append(chunk)
                    yield chunk

            if not had_error_from_provider:
                # Success — no need to try other providers
                return

            # If we get here, the provider failed and we'll try the next one
            # If this was the last provider in chain, yield the last error
            if attempt_index == len(provider_chain) - 1:
                logger.error(
                    "All providers in failover chain failed",
                    extra={
                        "event_type": "all_providers_failed",
                        "provider_chain": provider_chain,
                        "last_error": last_error,
                    },
                )
                yield {
                    "type": "error",
                    "content": last_error or "All providers failed. Please try again later.",
                }

    async def stream_with_fallback(
        self, messages: list[dict], model_type: str
    ) -> AsyncGenerator[dict, None]:
        """Legacy alias — delegates to stream()."""
        async for chunk in self.stream(messages, model_type):
            yield chunk


# Global LLM Router instance
llm_router = LLMRouter()
