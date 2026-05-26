import uuid
import logging
import asyncio
from datetime import datetime
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import Message
from app.db.repositories.message_repository import MessageRepository
from app.db.repositories.conversation_repository import ConversationRepository
from app.services.llm_router import llm_router
from app.core.cache import get_cache, invalidate_conversation_cache

logger = logging.getLogger(__name__)

class ChatService:
    @staticmethod
    async def create_user_message(
        db: AsyncSession,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID,
        content: str
    ) -> None:
        """Log the user's input message with deduplication and verify conversation ownership.
        
        Args:
            db: Database session
            user_id: ID of the user sending the message
            conversation_id: ID of the target conversation
            content: Message content (already validated)
            
        Raises:
            ValueError: If conversation not found or access denied
        """
        # Verify conversation exists and user owns it
        conversation = await ConversationRepository.get_by_id_and_user_id(db, conversation_id, user_id)
        if not conversation:
            raise ValueError("Conversation not found or access denied.")
        
        # Check for duplicate messages (prevent race condition on rapid sends)
        # Get the most recent message
        stmt = select(Message).where(
            Message.conversation_id == conversation_id,
            Message.role == "user"
        ).order_by(Message.created_at.desc()).limit(1)
        result = await db.execute(stmt)
        last_message = result.scalar_one_or_none()
        
        # If the last message has identical content and was created in the last 2 seconds,
        # it's likely a duplicate from the user clicking send twice
        if last_message and last_message.content == content:
            time_diff = datetime.utcnow() - last_message.created_at
            if time_diff.total_seconds() < 2:
                logger.warning(f"Duplicate message detected for conversation={conversation_id}, skipping.")
                return
        
        # Save user message
        await MessageRepository.create(
            db=db,
            conversation_id=conversation_id,
            role="user",
            content=content
        )

        # Update conversation timestamp
        conversation.updated_at = datetime.utcnow()
        db.add(conversation)
        
        # Auto-rename conversation if it's the first message
        history = await MessageRepository.get_history(db, conversation_id, limit=2)
        if len(history) <= 1 and conversation.title == "New Conversation":
            # Set title to first 50 chars of the message
            title = content[:50] + ("..." if len(content) > 50 else "")
            await ConversationRepository.update_title(db, conversation, title)
        
        # Explicitly flush to ensure message is persisted
        await db.flush()
        await db.commit()
        await invalidate_conversation_cache(get_cache(), str(user_id), str(conversation_id))

    @staticmethod
    async def stream_chat_response(
        db: AsyncSession,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID,
        model_type: str
    ) -> AsyncGenerator[dict, None]:
        """Stream LLM response with proper error handling and persistence.
        
        Yields streaming chunks and persists the final accumulated response.
        Handles timeouts and cancellations gracefully.
        
        Args:
            db: Database session
            user_id: ID of the user
            conversation_id: ID of the conversation
            model_type: Type of model to use (default, fast, reasoning)
            
        Yields:
            Dict with streaming events: {type: 'delta'|'done'|'error', content: str, ...}
        """
        # Verify conversation ownership
        conversation = await ConversationRepository.get_by_id_and_user_id(db, conversation_id, user_id)
        if not conversation:
            yield {"type": "error", "content": "Conversation access denied."}
            return

        try:
            # Load message history (limit to last 40 messages to control context size)
            db_messages = await MessageRepository.get_history(db, conversation_id, limit=40)
            
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
            
            # Stream response from LLM router
            accumulated_content = []
            provider_used = None
            model_used = None
            stream_error = None
            
            async for chunk in llm_router.stream(messages_payload, model_type):
                if chunk["type"] == "delta":
                    accumulated_content.append(chunk["content"])
                    provider_used = chunk.get("provider")
                    model_used = chunk.get("model")
                    yield chunk
                elif chunk["type"] == "error":
                    stream_error = chunk.get("content", "Unknown error")
                    logger.error(f"Stream error: {stream_error}")
                    yield chunk
                    return
            
            # Persist accumulated response to database
            full_text = "".join(accumulated_content)
            if not full_text:
                logger.warning(f"Empty response for conversation={conversation_id}")
                yield {"type": "error", "content": "No response generated. Please try again."}
                return
            
            try:
                # Save assistant message with metadata
                await MessageRepository.create(
                    db=db,
                    conversation_id=conversation_id,
                    role="assistant",
                    content=full_text,
                    model_used=model_used,
                    provider_used=provider_used
                )
                
                # Update conversation's updated_at timestamp
                conversation.updated_at = datetime.utcnow()
                db.add(conversation)
                
                # Flush and commit with explicit error handling
                await db.flush()
                await db.commit()
                await invalidate_conversation_cache(get_cache(), str(user_id), str(conversation_id))
                
                logger.info(
                    f"Persisted assistant message",
                    extra={
                        "conversation_id": str(conversation_id),
                        "model": model_used,
                        "provider": provider_used,
                        "content_length": len(full_text)
                    }
                )
                
            except Exception as e:
                await db.rollback()
                logger.error(
                    f"Failed to persist assistant response: {e}",
                    extra={"conversation_id": str(conversation_id)},
                    exc_info=True
                )
                yield {"type": "error", "content": "Failed to save response to database. Response was not persisted."}
                return
            
            # Emit final completion event
            yield {
                "type": "done",
                "content": full_text
            }
            
        except asyncio.CancelledError:
            logger.info(
                "Stream cancelled before completion",
                extra={"conversation_id": str(conversation_id)}
            )
            return
        except Exception as e:
            logger.error(
                f"Unexpected error in stream_chat_response: {e}",
                extra={"conversation_id": str(conversation_id)},
                exc_info=True
            )
            yield {"type": "error", "content": "An unexpected error occurred during streaming."}
            return
