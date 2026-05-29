import json
import logging
import asyncio
import time
from typing import AsyncGenerator
import httpx
from app.providers.base import BaseLLMProvider
from app.core.observability import get_stream_context
from app.core.time import utc_now
from app.core.observability.structured_logger import get_logger
from app.core.observability.metrics import get_metrics, MetricType, Metric

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Per-model configuration overrides
# ---------------------------------------------------------------------------
# These are merged on top of the class-level defaults when the provider is
# invoked with a matching model name.  Unknown models fall back to the
# class-level defaults.
MODEL_CONFIGS: dict[str, dict] = {
    "qwen/qwen3.5-122b-a10b": {
        "max_tokens": 16384,
        "temperature": 0.60,
        "top_p": 0.95,
        "chat_template_kwargs": {"enable_thinking": True},
    },
    "google/gemma-3n-e4b-it": {
        "max_tokens": 512,
        "temperature": 0.20,
        "top_p": 0.70,
        "frequency_penalty": 0.00,
        "presence_penalty": 0.00,
    },
}


class NvidiaProvider(BaseLLMProvider):
    """NVIDIA AI provider for streaming chat completions.

    Handles streaming from NVIDIA's inference API with proper timeouts,
    retry logic, error handling, and resource cleanup.

    Model-specific parameters (max_tokens, temperature, top_p, thinking
    mode, frequency_penalty, presence_penalty) are read from
    ``MODEL_CONFIGS`` and merged on top of the class-level defaults.
    """

    # ---- Class-level defaults (overridden by MODEL_CONFIGS entries) ----
    BASE_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
    REQUEST_TIMEOUT = 30.0
    STREAM_TIMEOUT = 120.0
    CHUNK_TIMEOUT = 10.0
    MAX_RETRIES = 2
    RETRY_DELAY = 1.0
    TEMPERATURE = 0.20
    MAX_TOKENS = 2048
    TOP_P = 0.90

    def __init__(self, api_key: str | None):
        self.api_key = api_key
        self.base_url = self.BASE_URL

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_model_config(self, model: str) -> dict:
        """Return per-model overrides for *model*, or an empty dict."""
        return MODEL_CONFIGS.get(model, {})

    def _get_headers(self) -> dict:
        """Get authorization headers for NVIDIA API."""
        if not self.api_key:
            raise ValueError("NVIDIA_API_KEY is not configured.")

        cleaned_api_key = self.api_key.strip('"').strip("'").strip()

        return {
            "Authorization": f"Bearer {cleaned_api_key}",
            "Content-Type": "application/json",
        }

    def _build_payload(self, model: str, messages: list[dict], stream: bool = True) -> dict:
        """Build the request payload, merging per-model config overrides."""
        cfg = self._get_model_config(model)

        payload: dict = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "temperature": cfg.get("temperature", self.TEMPERATURE),
            "max_tokens": cfg.get("max_tokens", self.MAX_TOKENS),
            "top_p": cfg.get("top_p", self.TOP_P),
        }

        # Optional parameters that only some models support
        if "frequency_penalty" in cfg:
            payload["frequency_penalty"] = cfg["frequency_penalty"]
        if "presence_penalty" in cfg:
            payload["presence_penalty"] = cfg["presence_penalty"]
        if "chat_template_kwargs" in cfg:
            payload["chat_template_kwargs"] = cfg["chat_template_kwargs"]

        return payload

    # ------------------------------------------------------------------
    # Streaming
    # ------------------------------------------------------------------

    async def _execute_stream(
        self, client: httpx.AsyncClient, headers: dict, payload: dict, model: str
    ) -> AsyncGenerator[dict, None]:
        """Execute a single streaming request and yield parsed chunks."""
        stream_ctx = get_stream_context()
        request_start = utc_now()
        
        try:
            async with client.stream(
                "POST",
                self.base_url,
                headers=headers,
                json=payload,
                timeout=httpx.Timeout(
                    timeout=self.STREAM_TIMEOUT,
                    read=self.CHUNK_TIMEOUT,
                ),
            ) as response:
                # Record provider request time
                if stream_ctx:
                    stream_ctx.provider_request_time = request_start
                
                if response.status_code == 429:
                    # Rate limit
                    error_body = await response.aread()
                    error_msg = error_body.decode("utf-8", errors="ignore")
                    get_metrics().increment_provider_rate_limits()
                    logger.warning(
                        "NVIDIA API rate limit hit",
                        extra={
                            "status_code": response.status_code,
                            "model": model,
                            "provider": "nvidia",
                        },
                    )
                    yield {
                        "type": "error",
                        "content": f"NVIDIA API rate limited. Please try again later.",
                    }
                    return
                
                if response.status_code != 200:
                    error_body = await response.aread()
                    error_msg = error_body.decode("utf-8", errors="ignore")
                    logger.error(
                        "NVIDIA API error",
                        extra={
                            "status_code": response.status_code,
                            "model": model,
                            "error": error_msg[:200],
                            "provider": "nvidia",
                            "error_category": "provider_error",
                        },
                    )
                    yield {
                        "type": "error",
                        "content": f"NVIDIA API returned status {response.status_code}. Please try again.",
                    }
                    return

                chunk_count = 0
                async for line in response.aiter_lines():
                    if not line or not line.strip():
                        continue

                    if line.startswith("data:"):
                        data_str = line[5:].strip()

                        if data_str == "[DONE]":
                            logger.debug(
                                f"NVIDIA stream completed",
                                extra={
                                    "model": model,
                                    "provider": "nvidia",
                                    "chunk_count": chunk_count,
                                },
                            )
                            break

                        try:
                            data_json = json.loads(data_str)
                            choices = data_json.get("choices", [])

                            if choices:
                                delta = choices[0].get("delta", {})
                                content = delta.get("content", "")

                                if content:
                                    chunk_count += 1
                                    # Record first token latency
                                    if chunk_count == 1 and stream_ctx:
                                        stream_ctx.first_token_time = utc_now()
                                    
                                    yield {
                                        "type": "delta",
                                        "content": content,
                                    }

                        except json.JSONDecodeError as e:
                            logger.warning(
                                "Failed to parse NVIDIA SSE chunk",
                                extra={
                                    "model": model,
                                    "error": str(e)[:100],
                                    "provider": "nvidia",
                                },
                            )
                            continue
                
                # Record provider response time
                if stream_ctx:
                    stream_ctx.provider_response_time = utc_now()
                    stream_ctx.provider_latency_ms = (
                        stream_ctx.provider_response_time - request_start
                    ).total_seconds() * 1000
                    
                    # Record metric
                    get_metrics().record_metric(
                        Metric(
                            metric_type=MetricType.PROVIDER_RESPONSE_TIME,
                            value=stream_ctx.provider_latency_ms,
                            timestamp=utc_now(),
                            tags={
                                'provider': 'nvidia',
                                'model': model,
                                'status': 'success',
                            }
                        )
                    )
                
        except Exception as e:
            logger.error(
                f"NVIDIA stream error: {e}",
                extra={
                    "model": model,
                    "provider": "nvidia",
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            raise

    async def stream_chat(
        self, messages: list[dict], model: str
    ) -> AsyncGenerator[dict, None]:
        """Stream chat response from NVIDIA API with retry support and observability."""
        headers = self._get_headers()
        payload = self._build_payload(model, messages, stream=True)
        full_content = []
        last_error = None
        stream_ctx = get_stream_context()
        metrics = get_metrics()

        for attempt in range(self.MAX_RETRIES + 1):
            if attempt > 0:
                metrics.increment_retries()
                logger.info(
                    "Retrying NVIDIA streaming request",
                    extra={
                        "model": model,
                        "attempt": attempt + 1,
                        "max_retries": self.MAX_RETRIES,
                        "provider": "nvidia",
                    },
                )
                stream_ctx = get_stream_context()
                if stream_ctx:
                    stream_ctx.retry_count = attempt
                await asyncio.sleep(self.RETRY_DELAY * attempt)

            try:
                async with httpx.AsyncClient(timeout=self.REQUEST_TIMEOUT) as client:
                    chunk_count = 0
                    async for chunk in self._execute_stream(
                        client, headers, payload, model
                    ):
                        if chunk["type"] == "delta":
                            full_content.append(chunk["content"])
                            chunk_count += 1
                            if stream_ctx:
                                stream_ctx.chunk_count += 1
                            yield chunk
                        elif chunk["type"] == "error":
                            last_error = chunk["content"]
                            break

                    if chunk_count > 0:
                        logger.info(
                            "NVIDIA stream completed successfully",
                            extra={
                                "model": model,
                                "provider": "nvidia",
                                "chunk_count": chunk_count,
                            },
                        )
                        break

            except httpx.TimeoutException as e:
                metrics.increment_provider_timeouts()
                logger.warning(
                    "NVIDIA stream timeout",
                    extra={
                        "model": model,
                        "attempt": attempt + 1,
                        "max_retries": self.MAX_RETRIES,
                        "timeout_type": type(e).__name__,
                        "provider": "nvidia",
                        "error_category": "provider_timeout",
                    },
                )
                if full_content:
                    logger.info(
                        "NVIDIA timeout - returning partial response",
                        extra={
                            "model": model,
                            "provider": "nvidia",
                            "partial_content_length": len("".join(full_content)),
                        },
                    )
                    yield {"type": "done", "content": "".join(full_content)}
                    return
                last_error = f"Request to NVIDIA API timed out (attempt {attempt + 1})"
                if attempt < self.MAX_RETRIES:
                    continue
                else:
                    break

            except httpx.HTTPError as e:
                last_error = f"HTTP error: {str(e)[:100]}"
                logger.warning(
                    "NVIDIA HTTP error",
                    extra={
                        "model": model,
                        "attempt": attempt + 1,
                        "max_retries": self.MAX_RETRIES,
                        "error_type": type(e).__name__,
                        "provider": "nvidia",
                        "error_category": "provider_error",
                    },
                )
                if attempt < self.MAX_RETRIES:
                    continue
                else:
                    break

            except Exception as e:
                last_error = f"Unexpected error: {str(e)[:100]}"
                logger.error(
                    "NVIDIA unexpected error in streaming",
                    extra={
                        "model": model,
                        "attempt": attempt + 1,
                        "max_retries": self.MAX_RETRIES,
                        "provider": "nvidia",
                        "error_type": type(e).__name__,
                    },
                    exc_info=True,
                )
                if attempt < self.MAX_RETRIES:
                    continue
                else:
                    break

        if full_content:
            content = "".join(full_content)
            if stream_ctx:
                stream_ctx.total_tokens = len(content.split())
            yield {"type": "done", "content": content}
        elif last_error:
            metrics.increment_failed_requests()
            logger.error(
                "NVIDIA stream failed",
                extra={
                    "model": model,
                    "provider": "nvidia",
                    "error": last_error,
                    "attempts": self.MAX_RETRIES + 1,
                },
            )
            yield {"type": "error", "content": last_error}

    # ------------------------------------------------------------------
    # Non-streaming (unused but required by interface)
    # ------------------------------------------------------------------

    async def chat(self, messages: list[dict], model: str) -> dict:
        """Get non-streaming chat response."""
        headers = self._get_headers()
        payload = self._build_payload(model, messages, stream=False)

        for attempt in range(self.MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=self.REQUEST_TIMEOUT) as client:
                    response = await client.post(
                        self.base_url, headers=headers, json=payload
                    )

                    if response.status_code != 200:
                        logger.error(
                            "NVIDIA API error (non-streaming)",
                            extra={
                                "status_code": response.status_code,
                                "model": model,
                            },
                        )
                        if attempt < self.MAX_RETRIES:
                            await asyncio.sleep(self.RETRY_DELAY * (attempt + 1))
                            continue
                        raise ValueError(
                            f"NVIDIA API returned error: {response.status_code}"
                        )

                    data = response.json()
                    content = data["choices"][0]["message"]["content"]

                    return {
                        "content": content,
                        "model": model,
                        "provider": "nvidia",
                    }

            except httpx.TimeoutException:
                logger.error(
                    f"Request timeout for model={model} (attempt {attempt + 1})"
                )
                if attempt < self.MAX_RETRIES:
                    await asyncio.sleep(self.RETRY_DELAY * (attempt + 1))
                    continue
                raise ValueError("NVIDIA API request timed out after retries")
            except Exception as e:
                logger.error(f"Error in NVIDIA chat: {e}", exc_info=True)
                if attempt < self.MAX_RETRIES:
                    await asyncio.sleep(self.RETRY_DELAY * (attempt + 1))
                    continue
                raise
