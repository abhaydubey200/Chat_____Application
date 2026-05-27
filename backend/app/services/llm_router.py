import logging
from typing import AsyncGenerator
from app.core.config import settings
from app.providers.registry import provider_registry
from app.core.observability import get_logger, get_stream_context

logger = get_logger(__name__)

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
        """Route message stream to the configured LLM provider and model.
        
        Includes comprehensive observability for provider selection and routing.
        """
        provider_name = self.provider_name
        resolved_model = self.resolve_model(model_type)
        stream_ctx = get_stream_context()
        
        logger.debug(
            "Routing streaming request to LLM provider",
            extra={
                "event_type": "routing_request",
                "provider": provider_name,
                "model_type": model_type,
                "resolved_model": resolved_model,
                "message_count": len(messages),
            }
        )
        
        try:
            provider = provider_registry.get_provider(provider_name)
            logger.debug(
                f"Provider loaded: {provider_name}",
                extra={
                    "event_type": "provider_loaded",
                    "provider": provider_name,
                    "provider_class": type(provider).__name__,
                }
            )
        except Exception as e:
            error_msg = f"Failed to fetch provider: {e}"
            logger.error(
                error_msg,
                extra={
                    "event_type": "provider_load_error",
                    "provider": provider_name,
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            yield {
                "type": "error",
                "content": f"Failed to load provider '{provider_name}': {str(e)}"
            }
            return
        
        # Update stream context with provider info
        if stream_ctx:
            stream_ctx.provider_name = provider_name
            stream_ctx.model_name = resolved_model
        
        # Call provider streaming generator
        try:
            async for chunk in provider.stream_chat(messages, resolved_model):
                # Inject metadata on delta or done events
                if chunk["type"] in ("delta", "done"):
                    chunk["provider"] = provider_name
                    chunk["model"] = resolved_model
                yield chunk
        except Exception as e:
            logger.error(
                f"Provider streaming failed: {e}",
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
                "content": f"Provider error: {str(e)}"
            }

# Global LLM Router instance
llm_router = LLMRouter()
