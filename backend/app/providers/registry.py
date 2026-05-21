from app.core.config import settings
from app.providers.base import BaseLLMProvider
from app.providers.nvidia import NvidiaProvider
from app.providers.gemini import GeminiProvider

class ProviderRegistry:
    def __init__(self):
        self._providers = {}
        # Initialize providers lazily or instantly
        self._providers["nvidia"] = NvidiaProvider(api_key=settings.NVIDIA_API_KEY)
        self._providers["gemini"] = GeminiProvider(api_key=settings.GEMINI_API_KEY)

    def get_provider(self, name: str) -> BaseLLMProvider:
        """Retrieve a provider instance by its name.
        
        Args:
            name: The lowercase name of the provider (e.g. 'nvidia', 'gemini')
        """
        provider = self._providers.get(name.lower())
        if not provider:
            available = list(self._providers.keys())
            raise ValueError(f"Unknown LLM provider '{name}'. Available providers: {available}")
        return provider

# Global registry instance
provider_registry = ProviderRegistry()
