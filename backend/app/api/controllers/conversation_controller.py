import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.db.repositories.conversation_repository import ConversationRepository
from app.db.repositories.message_repository import MessageRepository
from app.api.schemas import ConversationCreate, ConversationUpdate, ConversationResponse, ConversationDetailResponse, MessageResponse
from app.core.cache import (
    get_cache,
    cache_json_get,
    cache_json_set,
    conversation_list_key,
    conversation_detail_key,
    invalidate_conversation_cache,
)
from app.core.config import settings
from app.core.security_utils import sanitize_title
from app.services.audit_service import AuditService

class ConversationController:
    @staticmethod
    async def create(db: AsyncSession, user_id: uuid.UUID, create_data: ConversationCreate, organization_id: uuid.UUID | None = None) -> ConversationResponse:
        """Create a new conversation room."""
        sanitized_title = sanitize_title(create_data.title)
        conversation = await ConversationRepository.create(db, user_id, sanitized_title, organization_id=organization_id)
        await db.commit()
        await invalidate_conversation_cache(get_cache(), str(user_id))
        AuditService.append_background(
            event_type="conversation_created",
            status="success",
            user_id=user_id,
            organization_id=organization_id,
            conversation_id=conversation.id,
            metadata={"title": conversation.title},
        )
        return conversation

    @staticmethod
    async def list_conversations(db: AsyncSession, user_id: uuid.UUID) -> list[ConversationResponse]:
        """Fetch all conversations belonging to the current user."""
        cache = get_cache()
        if cache:
            cached = await cache_json_get(cache, conversation_list_key(str(user_id)))
            if cached is not None:
                return [ConversationResponse.model_validate(item) for item in cached]
        conversations = await ConversationRepository.list_by_user_id(db, user_id)
        if cache:
            payload = [
                ConversationResponse.model_validate(item).model_dump(mode="json")
                for item in conversations
            ]
            await cache_json_set(
                cache,
                conversation_list_key(str(user_id)),
                payload,
                settings.REDIS_CACHE_TTL_SECONDS,
            )
        return conversations

    @staticmethod
    async def get_conversation_detail(
        db: AsyncSession,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID
    ) -> ConversationDetailResponse:
        """Fetch conversation details including chat message history."""
        cache = get_cache()
        if cache:
            cached = await cache_json_get(
                cache,
                conversation_detail_key(str(user_id), str(conversation_id)),
            )
            if cached is not None:
                return ConversationDetailResponse.model_validate(cached)
        conversation = await ConversationRepository.get_by_id_and_user_id(db, conversation_id, user_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found or access denied."
            )
        
        messages = await MessageRepository.get_history(db, conversation_id, limit=100)
        payload = {
            "conversation": ConversationResponse.model_validate(conversation).model_dump(mode="json"),
            "messages": [
                MessageResponse.model_validate(item).model_dump(mode="json")
                for item in messages
            ],
        }
        if cache:
            await cache_json_set(
                cache,
                conversation_detail_key(str(user_id), str(conversation_id)),
                payload,
                settings.REDIS_CACHE_TTL_SECONDS,
            )
        return payload

    @staticmethod
    async def update_conversation(
        db: AsyncSession,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID,
        update_data: ConversationUpdate
    ) -> ConversationResponse:
        """Rename an existing conversation."""
        conversation = await ConversationRepository.get_by_id_and_user_id(db, conversation_id, user_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found or access denied."
            )
        
        sanitized_title = sanitize_title(update_data.title)
        updated_conv = await ConversationRepository.update_title(db, conversation, sanitized_title)
        await db.commit()
        await invalidate_conversation_cache(get_cache(), str(user_id), str(conversation_id))
        AuditService.append_background(
            event_type="conversation_renamed",
            status="success",
            user_id=user_id,
            organization_id=conversation.organization_id,
            conversation_id=conversation_id,
            metadata={"new_title": update_data.title},
        )
        return updated_conv

    @staticmethod
    async def delete_conversation(
        db: AsyncSession,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID
    ) -> dict:
        """Remove a conversation and its messages."""
        conversation = await ConversationRepository.get_by_id_and_user_id(db, conversation_id, user_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found or access denied."
            )
        
        await ConversationRepository.delete(db, conversation)
        await db.commit()
        await invalidate_conversation_cache(get_cache(), str(user_id), str(conversation_id))
        AuditService.append_background(
            event_type="conversation_deleted",
            status="success",
            user_id=user_id,
            organization_id=conversation.organization_id,
            conversation_id=conversation_id,
        )
        return {"status": "success", "message": "Conversation deleted."}
