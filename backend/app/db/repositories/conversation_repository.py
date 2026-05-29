import uuid
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Conversation
from app.core.time import utc_now

class ConversationRepository:
    @staticmethod
    async def create(
        db: AsyncSession,
        user_id: uuid.UUID,
        title: str,
        organization_id: uuid.UUID | None = None,
    ) -> Conversation:
        """Create a new conversation."""
        conversation = Conversation(user_id=user_id, title=title, organization_id=organization_id)
        db.add(conversation)
        await db.flush()
        return conversation

    @staticmethod
    async def get_by_id_and_user_id(db: AsyncSession, conversation_id: uuid.UUID, user_id: uuid.UUID) -> Conversation | None:
        """Fetch a conversation by ID and verify user ownership."""
        stmt = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
            Conversation.deleted_at.is_(None),
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_by_user_id(db: AsyncSession, user_id: uuid.UUID, limit: int = 100, offset: int = 0) -> list[Conversation]:
        """List all conversations for a user, sorted by update time."""
        stmt = select(Conversation).where(
            Conversation.user_id == user_id,
            Conversation.deleted_at.is_(None),
        ).order_by(
            desc(Conversation.updated_at)
        ).limit(limit).offset(offset)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def update_title(db: AsyncSession, conversation: Conversation, title: str) -> Conversation:
        """Update the title of a conversation."""
        conversation.title = title
        db.add(conversation)
        await db.flush()
        return conversation

    @staticmethod
    async def delete(db: AsyncSession, conversation: Conversation) -> None:
        """Soft delete a conversation."""
        conversation.deleted_at = conversation.deleted_at or utc_now()
        db.add(conversation)
        await db.flush()
_ = ConversationRepository
