import json
from typing import AsyncGenerator
import httpx
from app.providers.base import BaseLLMProvider
from app.core.observability import get_logger

logger = get_logger(__name__)


class GeminiProvider(BaseLLMProvider):
    """Google Gemini AI provider for streaming chat completions.

    Uses OpenAI-compatible endpoint for seamless integration.
    Handles streaming with proper timeouts, error handling, and cleanup.
    """

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    REQUEST_TIMEOUT = 30.0
    STREAM_TIMEOUT = 120.0
    CHUNK_TIMEOUT = 10.0
    TEMPERATURE = 0.2
    MAX_TOKENS = 2048

    def __init__(self, api_key: str | None):
        self.api_key = api_key
        self.base_url = self.BASE_URL

    def _get_headers(self) -> dict:
        """Get authentication headers for Gemini API.

        Returns:
            dict: Headers with Bearer token

        Raises:
            ValueError: If API key not configured
        """
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured.")
        cleaned_api_key = self.api_key.strip('"').strip("'").strip()
        return {
            "Authorization": f"Bearer {cleaned_api_key}",
            "Content-Type": "application/json",
        }

    def _build_payload(self, model: str, messages: list[dict], stream: bool = True) -> dict:
        """Build the request payload for the Gemini API."""
        return {
            "model": model,
            "messages": messages,
            "stream": stream,
            "temperature": self.TEMPERATURE,
            "max_tokens": self.MAX_TOKENS,
        }

    async def stream_chat(
        self, messages: list[dict], model: str
    ) -> AsyncGenerator[dict, None]:
        """Stream chat response from Gemini API token by token.

        Args:
            messages: Conversation history [{role: str, content: str}]
            model: Model name to use

        Yields:
            dict: Chunks with type (delta/done/error) and content
        """
        headers = self._get_headers()
        payload = self._build_payload(model, messages, stream=True)
        full_content = []

        try:
            async with httpx.AsyncClient(timeout=self.REQUEST_TIMEOUT) as client:
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
                        if response.status_code != 200:
                            error_body = await response.aread()
                            error_msg = error_body.decode("utf-8", errors="ignore")
                            logger.error(
                                "Gemini API error",
                                extra={
                                    "status_code": response.status_code,
                                    "model": model,
                                    "error": error_msg[:200],
                                },
                            )
                            yield {
                                "type": "error",
                                "content": f"Gemini API returned status {response.status_code}. Please try again.",
                            }
                            return

                        async for line in response.aiter_lines():
                            if not line or not line.strip():
                                continue

                            if line.startswith("data:"):
                                data_str = line[5:].strip()
                                if data_str == "[DONE]":
                                    break

                                try:
                                    data_json = json.loads(data_str)
                                    choices = data_json.get("choices", [])
                                    if choices:
                                        delta = choices[0].get("delta", {})
                                        content = delta.get("content", "")
                                        if content:
                                            full_content.append(content)
                                            yield {"type": "delta", "content": content}
                                except json.JSONDecodeError:
                                    logger.warning(
                                        "Failed to parse SSE line from Gemini API",
                                        extra={"model": model},
                                    )
                                    continue

                except httpx.TimeoutException as e:
                    logger.error(
                        "Stream timeout from Gemini API",
                        extra={
                            "model": model,
                            "timeout_type": type(e).__name__,
                        },
                    )
                    if full_content:
                        yield {"type": "done", "content": "".join(full_content)}
                    else:
                        yield {
                            "type": "error",
                            "content": "Request to Gemini API timed out. Please try again.",
                        }
                    return

        except httpx.HTTPError as e:
            logger.error(
                "HTTP error connecting to Gemini API",
                extra={"model": model, "error_type": type(e).__name__},
                exc_info=True,
            )
            yield {
                "type": "error",
                "content": f"Connection to Gemini API failed: {str(e)[:100]}",
            }
            return
        except Exception as e:
            logger.error(
                "Unexpected error in Gemini streaming",
                extra={"model": model},
                exc_info=True,
            )
            yield {
                "type": "error",
                "content": "An unexpected error occurred. Please try again.",
            }
            return

        # Emit final accumulated response
        yield {
            "type": "done",
            "content": "".join(full_content),
        }

    async def chat(self, messages: list[dict], model: str) -> dict:
        """Get non-streaming chat response from Gemini API.

        Args:
            messages: Conversation history
            model: Model name to use

        Returns:
            dict: Response with content, model, and provider fields

        Raises:
            ValueError: If API returns error status
        """
        headers = self._get_headers()
        payload = self._build_payload(model, messages, stream=False)

        try:
            async with httpx.AsyncClient(timeout=self.REQUEST_TIMEOUT) as client:
                response = await client.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                )

                if response.status_code != 200:
                    logger.error(
                        "Gemini API error (non-streaming)",
                        extra={"status_code": response.status_code, "model": model},
                    )
                    raise ValueError(
                        f"Gemini API returned error status {response.status_code}: {response.text}"
                    )

                data = response.json()
                content = data["choices"][0]["message"]["content"]
                return {
                    "content": content,
                    "model": model,
                    "provider": "gemini",
                }

        except httpx.TimeoutException:
            logger.error(f"Request timeout for model={model}")
            raise ValueError("Gemini API request timed out")
        except Exception as e:
            logger.error(f"Error in Gemini chat: {e}", exc_info=True)
            raise
