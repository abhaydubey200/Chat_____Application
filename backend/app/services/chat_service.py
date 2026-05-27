import uuid
import asyncio
import time
from datetime import datetime
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import Message
from app.db.repositories.message_repository import MessageRepository
from app.db.repositories.conversation_repository import ConversationRepository
from app.services.llm_router import llm_router
from app.services.audit_service import AuditService
from app.services.usage_service import UsageService, TokenEstimator
from app.services.provider_policy_service import ProviderPolicyService
from app.services.security_event_service import SecurityEventService
from app.core.config import settings
from app.core.cache import get_cache, invalidate_conversation_cache
from app.core.observability import (
    get_logger,
    get_stream_context,
    get_metrics,
)
from app.core.observability.error_types import get_error_category
from app.core.observability.metrics import Metric, MetricType

logger = get_logger(__name__)

class ChatService:
    @staticmethod
    async def create_user_message(
        db: AsyncSession,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID,
        content: str
    ) -> None:
        """Log the user's input message with deduplication and verify conversation ownership.
        
        Includes comprehensive observability for database operations and deduplication logic.
        
        Args:
            db: Database session
            user_id: ID of the user sending the message
            conversation_id: ID of the target conversation
            content: Message content (already validated)
            
        Raises:
            ValueError: If conversation not found or access denied
        """
        start_time = time.perf_counter()
        metrics = get_metrics()
        
        # Verify conversation exists and user owns it
        try:
            verify_start = time.perf_counter()
            conversation = await ConversationRepository.get_by_id_and_user_id(db, conversation_id, user_id)
            verify_duration = (time.perf_counter() - verify_start) * 1000
            
            logger.log_db_query(
                operation="SELECT",
                table="conversations",
                duration_ms=verify_duration,
                rows_affected=1 if conversation else 0,
            )
            
            if not conversation:
                logger.warning(
                    "Conversation not found or access denied",
                    extra={
                        "event_type": "conversation_not_found",
                        "user_id": str(user_id),
                        "conversation_id": str(conversation_id),
                    }
                )
                raise ValueError("Conversation not found or access denied.")
        except ValueError:
            raise
        except Exception as e:
            error_category = get_error_category(e)
            logger.error(
                "Error verifying conversation ownership",
                extra={
                    "event_type": "conversation_verify_error",
                    "error_type": type(e).__name__,
                    "error_category": error_category.value,
                },
                exc_info=True,
            )
            raise
        
        # Check for duplicate messages (prevent race condition on rapid sends)
        try:
            dedup_start = time.perf_counter()
            stmt = select(Message).where(
                Message.conversation_id == conversation_id,
                Message.role == "user"
            ).order_by(Message.created_at.desc()).limit(1)
            result = await db.execute(stmt)
            last_message = result.scalar_one_or_none()
            dedup_duration = (time.perf_counter() - dedup_start) * 1000
            
            logger.log_db_query(
                operation="SELECT",
                table="messages",
                duration_ms=dedup_duration,
                rows_affected=1 if last_message else 0,
            )
            
            # If the last message has identical content and was created in the last 2 seconds,
            # it's likely a duplicate from the user clicking send twice
            if last_message and last_message.content == content:
                time_diff = datetime.utcnow() - last_message.created_at
                if time_diff.total_seconds() < 2:
                    logger.warning(
                        "Duplicate message detected and skipped",
                        extra={
                            "event_type": "duplicate_message_detected",
                            "time_since_last_message_ms": time_diff.total_seconds() * 1000,
                        }
                    )
                    return
        except Exception as e:
            error_category = get_error_category(e)
            logger.error(
                "Error checking for duplicate messages",
                extra={
                    "event_type": "dedup_check_error",
                    "error_type": type(e).__name__,
                    "error_category": error_category.value,
                },
                exc_info=True,
            )
            raise
        
        # Save user message
        try:
            save_start = time.perf_counter()
            await MessageRepository.create(
                db=db,
                conversation_id=conversation_id,
                role="user",
                content=content
            )
            save_duration = (time.perf_counter() - save_start) * 1000
            
            logger.log_db_query(
                operation="INSERT",
                table="messages",
                duration_ms=save_duration,
                rows_affected=1,
            )
        except Exception as e:
            error_category = get_error_category(e)
            logger.error(
                "Failed to save user message",
                extra={
                    "event_type": "message_save_error",
                    "error_type": type(e).__name__,
                    "error_category": error_category.value,
                    "content_length": len(content),
                },
                exc_info=True,
            )
            raise

        # Update conversation timestamp
        conversation.updated_at = datetime.utcnow()
        db.add(conversation)
        
        # Auto-rename conversation if it's the first message
        try:
            hist_start = time.perf_counter()
            history = await MessageRepository.get_history(db, conversation_id, limit=2)
            hist_duration = (time.perf_counter() - hist_start) * 1000
            
            logger.log_db_query(
                operation="SELECT",
                table="messages",
                duration_ms=hist_duration,
                rows_affected=len(history),
            )
            
            if len(history) <= 1 and conversation.title == "New Conversation":
                # Set title to first 50 chars of the message
                title = content[:50] + ("..." if len(content) > 50 else "")
                await ConversationRepository.update_title(db, conversation, title)
                logger.debug(
                    "Conversation auto-titled",
                    extra={
                        "event_type": "conversation_auto_titled",
                        "title": title,
                    }
                )
        except Exception as e:
            error_category = get_error_category(e)
            logger.warning(
                "Failed to auto-title conversation",
                extra={
                    "event_type": "auto_title_error",
                    "error_type": type(e).__name__,
                    "error_category": error_category.value,
                },
            )
        
        # Explicitly flush to ensure message is persisted
        try:
            flush_start = time.perf_counter()
            await db.flush()
            await db.commit()
            flush_duration = (time.perf_counter() - flush_start) * 1000
            
            logger.log_db_query(
                operation="COMMIT",
                table="transactions",
                duration_ms=flush_duration,
                rows_affected=1,
            )
        except Exception as e:
            error_category = get_error_category(e)
            logger.error(
                "Failed to flush and commit user message",
                extra={
                    "event_type": "commit_error",
                    "error_type": type(e).__name__,
                    "error_category": error_category.value,
                },
                exc_info=True,
            )
            raise
        
        try:
            await invalidate_conversation_cache(get_cache(), str(user_id), str(conversation_id))
            logger.debug(
                "Conversation cache invalidated",
                extra={"event_type": "cache_invalidated"}
            )
        except Exception as e:
            logger.warning(
                "Failed to invalidate cache",
                extra={
                    "event_type": "cache_invalidation_error",
                    "error_type": type(e).__name__,
                }
            )
        
        total_duration = (time.perf_counter() - start_time) * 1000
        logger.debug(
            "User message creation completed",
            extra={
                "event_type": "user_message_created",
                "total_duration_ms": total_duration,
                "content_length": len(content),
            }
        )

    @staticmethod
    async def stream_chat_response(
        db: AsyncSession,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID,
        model_type: str,
        organization_id: uuid.UUID | None = None,
    ) -> AsyncGenerator[dict, None]:
        """Stream LLM response with proper error handling, persistence, and observability.
        
        Yields streaming chunks and persists the final accumulated response.
        Handles timeouts and cancellations gracefully with comprehensive logging.
        
        Args:
            db: Database session
            user_id: ID of the user
            conversation_id: ID of the conversation
            model_type: Type of model to use (default, fast, reasoning)
            
        Yields:
            Dict with streaming events: {type: 'delta'|'done'|'error', content: str, ...}
        """
        stream_ctx = get_stream_context()
        start_time = time.perf_counter()
        
        # Verify conversation ownership
        try:
            verify_start = time.perf_counter()
            conversation = await ConversationRepository.get_by_id_and_user_id(db, conversation_id, user_id)
            verify_duration = (time.perf_counter() - verify_start) * 1000
            
            logger.log_db_query(
                operation="SELECT",
                table="conversations",
                duration_ms=verify_duration,
                rows_affected=1 if conversation else 0,
            )
            
            if not conversation:
                logger.warning(
                    "Conversation access denied for stream",
                    extra={"event_type": "stream_access_denied"}
                )
                yield {"type": "error", "content": "Conversation access denied."}
                return
        except Exception as e:
            error_category = get_error_category(e)
            logger.error(
                "Error verifying conversation for stream",
                extra={
                    "event_type": "stream_verify_error",
                    "error_type": type(e).__name__,
                    "error_category": error_category.value,
                },
                exc_info=True,
            )
            yield {"type": "error", "content": "Failed to access conversation."}
            return

        try:
            # Load message history (limit to last 40 messages to control context size)
            hist_start = time.perf_counter()
            db_messages = await MessageRepository.get_history(db, conversation_id, limit=40)
            hist_duration = (time.perf_counter() - hist_start) * 1000
            
            logger.log_db_query(
                operation="SELECT",
                table="messages",
                duration_ms=hist_duration,
                rows_affected=len(db_messages),
            )
            
            logger.debug(
                "Loaded conversation history",
                extra={
                    "event_type": "history_loaded",
                    "message_count": len(db_messages),
                    "duration_ms": hist_duration,
                }
            )
            
            # Build message history for LLM
            messages_payload = []
            
            # Inject system prompt for consistent behavior
            messages_payload.append({
                "role": "system",
                "content": "You are Dushman AI, a production-grade conversational AI assistant. You answer queries precisely, write clean code, maintain professional tone, and are helpful and concise."
            })
            
            # Add conversation history
            for msg in db_messages:
                messages_payload.append({
                    "role": msg.role,
                    "content": msg.content
                })

            resolved_model = llm_router.resolve_model(model_type)
            provider_name = settings.LLM_PROVIDER
            input_tokens = TokenEstimator.estimate_messages_tokens(messages_payload, model=resolved_model)

            estimated_output_tokens = max(256, min(1024, int(input_tokens * 0.7)))
            cost_in, cost_out = await UsageService.get_model_pricing(
                organization_id, provider_name, resolved_model
            )
            estimated_cost = UsageService.estimate_cost(input_tokens, estimated_output_tokens, cost_in, cost_out)

            if organization_id:
                allowed, reason = await ProviderPolicyService.validate_provider_usage(
                    organization_id=organization_id,
                    provider_name=provider_name,
                    model_name=resolved_model,
                    model_type=model_type,
                    estimated_request_cost=estimated_cost,
                )
                if not allowed:
                    AuditService.append_background(
                        event_type="provider_policy_block",
                        status="blocked",
                        user_id=user_id,
                        organization_id=organization_id,
                        conversation_id=conversation_id,
                        provider_name=provider_name,
                        model_name=resolved_model,
                        metadata={"reason": reason},
                    )
                    await SecurityEventService.record_event(
                        event_type="provider_policy_block",
                        severity="medium",
                        user_id=user_id,
                        organization_id=organization_id,
                        metadata={"reason": reason},
                    )
                    yield {"type": "error", "content": reason or "Provider policy blocked request."}
                    return

            AuditService.append_background(
                event_type="provider_selected",
                status="success",
                user_id=user_id,
                organization_id=organization_id,
                conversation_id=conversation_id,
                provider_name=provider_name,
                model_name=resolved_model,
                input_tokens=input_tokens,
            )
            
            # Stream response from LLM router
            accumulated_content = []
            provider_used = None
            model_used = None
            stream_error = None
            
            logger.log_provider_request(
                provider_name="unknown",  # Will be set when first chunk arrives
                model_name=model_type,
                message_count=len(messages_payload),
            )
            
            async for chunk in llm_router.stream(messages_payload, model_type):
                if chunk["type"] == "delta":
                    accumulated_content.append(chunk["content"])
                    provider_used = chunk.get("provider")
                    model_used = chunk.get("model")
                    if stream_ctx:
                        stream_ctx.provider_name = provider_used or stream_ctx.provider_name
                        stream_ctx.model_name = model_used or stream_ctx.model_name
                    yield chunk
                elif chunk["type"] == "error":
                    stream_error = chunk.get("content", "Unknown error")
                    error_category = get_error_category(Exception(stream_error))
                    logger.error(
                        f"LLM stream error: {stream_error}",
                        extra={
                            "event_type": "llm_stream_error",
                            "error": stream_error,
                            "error_category": error_category.value,
                        }
                    )
                    yield chunk
                    if organization_id and provider_used and model_used:
                        await UsageService.record_usage(
                            user_id=user_id,
                            organization_id=organization_id,
                            conversation_id=conversation_id,
                            provider_name=provider_used,
                            model_name=model_used,
                            input_tokens=input_tokens,
                            output_tokens=0,
                            latency_ms=int((time.perf_counter() - start_time) * 1000),
                            stream_duration_ms=None,
                            retry_count=stream_ctx.retry_count if stream_ctx else 0,
                            status="error",
                        )
                    return
            
            # Persist accumulated response to database
            full_text = "".join(accumulated_content)
            if not full_text:
                logger.warning(
                    "Empty response generated by LLM",
                    extra={"event_type": "empty_response"}
                )
                yield {"type": "error", "content": "No response generated. Please try again."}
                return
            
            logger.debug(
                "LLM response generated",
                extra={
                    "event_type": "llm_response_complete",
                    "content_length": len(full_text),
                    "provider": provider_used,
                    "model": model_used,
                }
            )
            
            try:
                # Save assistant message with metadata
                save_start = time.perf_counter()
                await MessageRepository.create(
                    db=db,
                    conversation_id=conversation_id,
                    role="assistant",
                    content=full_text,
                    model_used=model_used,
                    provider_used=provider_used
                )
                save_duration = (time.perf_counter() - save_start) * 1000
                
                logger.log_db_query(
                    operation="INSERT",
                    table="messages",
                    duration_ms=save_duration,
                    rows_affected=1,
                )
                
                # Update conversation's updated_at timestamp
                conversation.updated_at = datetime.utcnow()
                db.add(conversation)
                
                # Flush and commit with explicit error handling
                commit_start = time.perf_counter()
                await db.flush()
                await db.commit()
                commit_duration = (time.perf_counter() - commit_start) * 1000
                
                logger.log_db_query(
                    operation="COMMIT",
                    table="transactions",
                    duration_ms=commit_duration,
                    rows_affected=1,
                )
                
                await invalidate_conversation_cache(get_cache(), str(user_id), str(conversation_id))
                
                logger.info(
                    "Assistant message persisted successfully",
                    extra={
                        "event_type": "assistant_message_persisted",
                        "content_length": len(full_text),
                        "model": model_used,
                        "provider": provider_used,
                        "save_duration_ms": save_duration,
                        "commit_duration_ms": commit_duration,
                    }
                )
                
            except Exception as e:
                await db.rollback()
                error_category = get_error_category(e)
                logger.error(
                    f"Failed to persist assistant response: {e}",
                    extra={
                        "event_type": "persistence_error",
                        "error_type": type(e).__name__,
                        "error_category": error_category.value,
                        "content_length": len(full_text),
                    },
                    exc_info=True,
                )
                yield {"type": "error", "content": "Failed to save response to database. Response was not persisted."}
                return

            output_tokens = TokenEstimator.estimate_text_tokens(full_text, model=model_used or resolved_model)
            if organization_id and provider_used and model_used:
                await UsageService.record_usage(
                    user_id=user_id,
                    organization_id=organization_id,
                    conversation_id=conversation_id,
                    provider_name=provider_used,
                    model_name=model_used,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    latency_ms=int((time.perf_counter() - start_time) * 1000),
                    stream_duration_ms=int((time.perf_counter() - start_time) * 1000),
                    retry_count=stream_ctx.retry_count if stream_ctx else 0,
                    status="success",
                )
                AuditService.append_background(
                    event_type="model_used",
                    status="success",
                    user_id=user_id,
                    organization_id=organization_id,
                    conversation_id=conversation_id,
                    provider_name=provider_used,
                    model_name=model_used,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    metadata={"model_type": model_type},
                )
            
            # Emit final completion event
            total_duration = (time.perf_counter() - start_time) * 1000
            logger.debug(
                "Stream response completed",
                extra={
                    "event_type": "stream_response_complete",
                    "total_duration_ms": total_duration,
                }
            )
            
            yield {
                "type": "done",
                "content": full_text
            }
            
        except asyncio.CancelledError:
            logger.info(
                "Stream cancelled before completion",
                extra={
                    "event_type": "stream_cancelled_before_completion",
                    "elapsed_ms": (time.perf_counter() - start_time) * 1000,
                }
            )
            return
        except Exception as e:
            error_category = get_error_category(e)
            logger.error(
                f"Unexpected error in stream_chat_response: {e}",
                extra={
                    "event_type": "stream_unexpected_error",
                    "error_type": type(e).__name__,
                    "error_category": error_category.value,
                    "elapsed_ms": (time.perf_counter() - start_time) * 1000,
                },
                exc_info=True,
            )
            yield {"type": "error", "content": "An unexpected error occurred during streaming."}
            return
