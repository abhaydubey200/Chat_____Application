import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Message

class MessageRepository:
    @staticmethod
    async def create(
        db: AsyncSession,
        conversation_id: uuid.UUID,
        role: str,
        content: str,
        model_used: str | None = None,
        provider_used: str | None = None
    ) -> Message:
        """Create and save a new message."""
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            model_used=model_used,
            provider_used=provider_used
        )
        db.add(message)
        await db.flush()
        return message

    @staticmethod
    async def get_history(db: AsyncSession, conversation_id: uuid.UUID, limit: int = 50) -> list[Message]:
        """Retrieve recent messages for a conversation, ordered chronologically."""
        stmt = select(Message).where(
            Message.conversation_id == conversation_id,
            Message.deleted_at.is_(None),
        ).order_by(
            Message.created_at.asc()
        ).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())
