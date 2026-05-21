import logging
from typing import AsyncGenerator
from app.core.config import settings
from app.providers.registry import provider_registry

logger = logging.getLogger(__name__)

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

    async def stream(self, messages: list[dict], model_type: str) -> AsyncGenerator[dict, None]:
        """Route message stream to the configured LLM provider and model."""
        provider_name = self.provider_name
        resolved_model = self.resolve_model(model_type)
        
        logger.info(f"Routing request to provider={provider_name}, model_type={model_type} (resolved: {resolved_model})")
        
        try:
            provider = provider_registry.get_provider(provider_name)
        except Exception as e:
            logger.error(f"Failed to fetch provider: {e}")
            yield {
                "type": "error",
                "content": f"Failed to load provider '{provider_name}': {str(e)}"
            }
            return
            
        # Call provider streaming generator
        async for chunk in provider.stream_chat(messages, resolved_model):
            # Inject metadata on delta or done events
            if chunk["type"] in ("delta", "done"):
                chunk["provider"] = provider_name
                chunk["model"] = resolved_model
            yield chunk

# Global LLM Router instance
llm_router = LLMRouter()
