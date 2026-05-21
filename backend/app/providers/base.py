from typing import AsyncGenerator
from abc import ABC, abstractmethod

class BaseLLMProvider(ABC):
    @abstractmethod
    async def stream_chat(self, messages: list[dict], model: str) -> AsyncGenerator[dict, None]:
        """Stream conversational responses from the provider token by token.
        
        Args:
            messages: Chronological conversation history [{"role": "user", "content": "..."}]
            model: The exact provider model string
            
        Yields:
            Dict containing normalized chunk data, e.g.:
            {"type": "delta", "content": "partial-token-text"}
            Or the final status:
            {"type": "done", "content": "full-text-accumulated"}
        """
        pass

    @abstractmethod
    async def chat(self, messages: list[dict], model: str) -> dict:
        """Fetch static non-streaming response.
        
        Args:
            messages: Chronological conversation history
            model: The exact provider model string
            
        Returns:
            Normalized response dict, e.g.:
            {"content": "full-text", "model": "...", "provider": "..."}
        """
        pass
