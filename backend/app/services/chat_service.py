import uuid
import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.repositories.message_repository import MessageRepository
from app.db.repositories.conversation_repository import ConversationRepository
from app.services.llm_router import llm_router

logger = logging.getLogger(__name__)

class ChatService:
    @staticmethod
    async def create_user_message(
        db: AsyncSession,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID,
        content: str
    ) -> None:
        """Log the user's input message and verify conversation ownership."""
        conversation = await ConversationRepository.get_by_id_and_user_id(db, conversation_id, user_id)
        if not conversation:
            raise ValueError("Conversation not found or access denied.")
        
        # Save user message
        await MessageRepository.create(
            db=db,
            conversation_id=conversation_id,
            role="user",
            content=content
        )
        
        # Micro-interaction: Auto-rename conversation if it still has the default title and this is the first message
        history = await MessageRepository.get_history(db, conversation_id, limit=2)
        if len(history) <= 1 and conversation.title == "New Conversation":
            # Set title to first 30 chars of the message
            title = content[:30] + ("..." if len(content) > 30 else "")
            await ConversationRepository.update_title(db, conversation, title)
            
        await db.commit()

    @staticmethod
    async def stream_chat_response(
        db: AsyncSession,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID,
        model_type: str
    ) -> AsyncGenerator[dict, None]:
        """Stream LLM response and persist the final output to the database."""
        conversation = await ConversationRepository.get_by_id_and_user_id(db, conversation_id, user_id)
        if not conversation:
            yield {"type": "error", "content": "Conversation access denied."}
            return

        # Load message history
        db_messages = await MessageRepository.get_history(db, conversation_id, limit=40)
        
        # Construct router input history
        messages_payload = []
        
        # Inject system prompt
        messages_payload.append({
            "role": "system",
            "content": "You are Dushman AI, a production-grade conversational AI assistant. You answer queries precisely, write clean code, and maintain professional tone."
        })
        
        for msg in db_messages:
            messages_payload.append({
                "role": msg.role,
                "content": msg.content
            })
            
        # Stream response
        accumulated_content = []
        provider_used = None
        model_used = None
        
        async for chunk in llm_router.stream(messages_payload, model_type):
            if chunk["type"] == "delta":
                accumulated_content.append(chunk["content"])
                provider_used = chunk.get("provider")
                model_used = chunk.get("model")
                yield chunk
            elif chunk["type"] == "error":
                yield chunk
                return
        
        # Persist assistant's final response to DB
        full_text = "".join(accumulated_content)
        if full_text:
            try:
                # Save message
                await MessageRepository.create(
                    db=db,
                    conversation_id=conversation_id,
                    role="assistant",
                    content=full_text,
                    model_used=model_used,
                    provider_used=provider_used
                )
                
                # Update conversation updated_at timestamp
                conversation.updated_at = conversation.updated_at # triggers update
                db.add(conversation)
                await db.commit()
                
                logger.info(f"Saved assistant message for conversation={conversation_id} model={model_used} provider={provider_used}")
            except Exception as e:
                logger.error(f"Failed to persist assistant response: {e}")
                await db.rollback()
                yield {"type": "error", "content": "Failed to save response to database."}
                return

        # Yield a final finish chunk with full content
        yield {
            "type": "done",
            "content": full_text
        }
