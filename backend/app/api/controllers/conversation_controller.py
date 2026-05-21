import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.db.repositories.conversation_repository import ConversationRepository
from app.db.repositories.message_repository import MessageRepository
from app.api.schemas import ConversationCreate, ConversationUpdate, ConversationResponse, ConversationDetailResponse

class ConversationController:
    @staticmethod
    async def create(db: AsyncSession, user_id: uuid.UUID, create_data: ConversationCreate) -> ConversationResponse:
        """Create a new conversation room."""
        conversation = await ConversationRepository.create(db, user_id, create_data.title)
        await db.commit()
        return conversation

    @staticmethod
    async def list_conversations(db: AsyncSession, user_id: uuid.UUID) -> list[ConversationResponse]:
        """Fetch all conversations belonging to the current user."""
        conversations = await ConversationRepository.list_by_user_id(db, user_id)
        return conversations

    @staticmethod
    async def get_conversation_detail(
        db: AsyncSession,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID
    ) -> ConversationDetailResponse:
        """Fetch conversation details including chat message history."""
        conversation = await ConversationRepository.get_by_id_and_user_id(db, conversation_id, user_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found or access denied."
            )
        
        messages = await MessageRepository.get_history(db, conversation_id, limit=100)
        return {
            "conversation": conversation,
            "messages": messages
        }

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
        
        updated_conv = await ConversationRepository.update_title(db, conversation, update_data.title)
        await db.commit()
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
        return {"status": "success", "message": "Conversation deleted."}
