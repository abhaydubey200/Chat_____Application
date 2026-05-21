import json
import logging
from typing import AsyncGenerator
import httpx
from app.providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)

class NvidiaProvider(BaseLLMProvider):
    def __init__(self, api_key: str | None):
        self.api_key = api_key
        self.base_url = "https://integrate.api.nvidia.com/v1/chat/completions"

    def _get_headers(self) -> dict:
        if not self.api_key:
            raise ValueError("NVIDIA_API_KEY is not configured.")
        cleaned_api_key = self.api_key.strip('"').strip("'")
        return {
            "Authorization": f"Bearer {cleaned_api_key}",
            "Content-Type": "application/json"
        }

    async def stream_chat(self, messages: list[dict], model: str) -> AsyncGenerator[dict, None]:
        headers = self._get_headers()
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "temperature": 0.2,
            "max_tokens": 1024
        }
        
        full_content = []
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                async with client.stream("POST", self.base_url, headers=headers, json=payload) as response:
                    if response.status_code != 200:
                        error_body = await response.aread()
                        logger.error(f"Nvidia API error: Status={response.status_code}, Body={error_body.decode()}")
                        yield {
                            "type": "error",
                            "content": f"Nvidia API returned status code {response.status_code}"
                        }
                        return
                    
                    async for line in response.aiter_lines():
                        if not line:
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
                                logger.warning(f"Failed to parse SSE line from Nvidia API: {line}")
                                continue
                                
            except httpx.HTTPError as e:
                logger.error(f"HTTP connection to Nvidia API failed: {e}")
                yield {
                    "type": "error",
                    "content": f"Connection to Nvidia API failed: {str(e)}"
                }
                return
                
        # Emit final accumulated response
        yield {
            "type": "done",
            "content": "".join(full_content)
        }

    async def chat(self, messages: list[dict], model: str) -> dict:
        headers = self._get_headers()
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "temperature": 0.2,
            "max_tokens": 1024
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(self.base_url, headers=headers, json=payload)
            if response.status_code != 200:
                raise ValueError(f"Nvidia API returned error status {response.status_code}: {response.text}")
            
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            return {
                "content": content,
                "model": model,
                "provider": "nvidia"
            }
