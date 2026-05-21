import json
import logging
from typing import AsyncGenerator
import httpx
from app.providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)

class NvidiaProvider(BaseLLMProvider):
    """NVIDIA AI provider for streaming chat completions.
    
    Handles streaming from NVIDIA's inference API with proper timeouts,
    error handling, and resource cleanup.
    """
    
    # Configuration constants
    BASE_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
    REQUEST_TIMEOUT = 30.0  # seconds
    STREAM_TIMEOUT = 120.0  # total time for entire stream
    CHUNK_TIMEOUT = 10.0  # time to receive next chunk
    MAX_RETRIES = 2
    TEMPERATURE = 0.2
    MAX_TOKENS = 2048
    
    def __init__(self, api_key: str | None):
        self.api_key = api_key
        self.base_url = self.BASE_URL

    def _get_headers(self) -> dict:
        """Get authorization headers for NVIDIA API.
        
        Returns:
            dict: Headers with Bearer token
            
        Raises:
            ValueError: If API key not configured
        """
        if not self.api_key:
            raise ValueError("NVIDIA_API_KEY is not configured.")
        
        # Clean up API key (remove quotes if present)
        cleaned_api_key = self.api_key.strip('"').strip("'").strip()
        
        return {
            "Authorization": f"Bearer {cleaned_api_key}",
            "Content-Type": "application/json"
        }

    async def stream_chat(
        self,
        messages: list[dict],
        model: str
    ) -> AsyncGenerator[dict, None]:
        """Stream chat response from NVIDIA API token by token.
        
        Args:
            messages: Conversation history [{role: str, content: str}]
            model: Model name to use
            
        Yields:
            dict: Chunks with type (delta/done/error) and content
            
        Note:
            - Implements timeouts to prevent resource leaks
            - Handles network errors gracefully
            - Accumulates full response for final persistence
        """
        headers = self._get_headers()
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "temperature": self.TEMPERATURE,
            "max_tokens": self.MAX_TOKENS
        }
        
        full_content = []
        
        try:
            async with httpx.AsyncClient(timeout=self.REQUEST_TIMEOUT) as client:
                try:
                    # Open streaming connection with timeout
                    async with client.stream(
                        "POST",
                        self.base_url,
                        headers=headers,
                        json=payload,
                        timeout=httpx.Timeout(
                            timeout=self.STREAM_TIMEOUT,
                            read=self.CHUNK_TIMEOUT
                        )
                    ) as response:
                        # Check for HTTP errors
                        if response.status_code != 200:
                            error_body = await response.aread()
                            error_msg = error_body.decode("utf-8", errors="ignore")
                            logger.error(
                                f"NVIDIA API error",
                                extra={
                                    "status_code": response.status_code,
                                    "model": model,
                                    "error": error_msg[:200]  # Truncate long errors
                                }
                            )
                            yield {
                                "type": "error",
                                "content": f"NVIDIA API returned status {response.status_code}. Please try again."
                            }
                            return
                        
                        # Process streaming response
                        async for line in response.aiter_lines():
                            if not line or not line.strip():
                                continue
                            
                            if line.startswith("data:"):
                                data_str = line[5:].strip()
                                
                                # Check for stream completion
                                if data_str == "[DONE]":
                                    logger.debug(f"Stream completed for model={model}")
                                    break
                                
                                # Parse and emit chunk
                                try:
                                    data_json = json.loads(data_str)
                                    choices = data_json.get("choices", [])
                                    
                                    if choices:
                                        delta = choices[0].get("delta", {})
                                        content = delta.get("content", "")
                                        
                                        if content:
                                            full_content.append(content)
                                            yield {
                                                "type": "delta",
                                                "content": content
                                            }
                                            
                                except json.JSONDecodeError as e:
                                    logger.warning(
                                        f"Failed to parse SSE chunk",
                                        extra={"model": model, "error": str(e)[:100]}
                                    )
                                    continue
                        
                except httpx.TimeoutException as e:
                    logger.error(
                        f"Stream timeout from NVIDIA API",
                        extra={"model": model, "timeout_type": type(e).__name__}
                    )
                    # If we got some content, it's better to return it than to fail
                    if full_content:
                        yield {"type": "done", "content": "".join(full_content)}
                    else:
                        yield {
                            "type": "error",
                            "content": "Request to NVIDIA API timed out. Please try again."
                        }
                    return
                    
        except httpx.HTTPError as e:
            logger.error(
                f"HTTP error connecting to NVIDIA API",
                extra={"model": model, "error_type": type(e).__name__},
                exc_info=True
            )
            yield {
                "type": "error",
                "content": f"Connection error: {str(e)[:100]}. Please try again."
            }
            return
        except Exception as e:
            logger.error(
                f"Unexpected error in NVIDIA streaming",
                extra={"model": model},
                exc_info=True
            )
            yield {
                "type": "error",
                "content": "An unexpected error occurred. Please try again."
            }
            return
        
        # Emit final accumulated response
        yield {
            "type": "done",
            "content": "".join(full_content)
        }

    async def chat(self, messages: list[dict], model: str) -> dict:
        """Get non-streaming chat response (currently unused but required by interface).
        
        Args:
            messages: Conversation history
            model: Model name to use
            
        Returns:
            dict: Response with content, model, and provider fields
            
        Raises:
            ValueError: If API returns error status
        """
        headers = self._get_headers()
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "temperature": self.TEMPERATURE,
            "max_tokens": self.MAX_TOKENS
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.REQUEST_TIMEOUT) as client:
                response = await client.post(
                    self.base_url,
                    headers=headers,
                    json=payload
                )
                
                if response.status_code != 200:
                    logger.error(
                        f"NVIDIA API error (non-streaming)",
                        extra={
                            "status_code": response.status_code,
                            "model": model
                        }
                    )
                    raise ValueError(f"NVIDIA API returned error: {response.status_code}")
                
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                
                return {
                    "content": content,
                    "model": model,
                    "provider": "nvidia"
                }
                
        except httpx.TimeoutException:
            logger.error(f"Request timeout for model={model}")
            raise ValueError("NVIDIA API request timed out")
        except Exception as e:
            logger.error(f"Error in NVIDIA chat: {e}", exc_info=True)
            raise
