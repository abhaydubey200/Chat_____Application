import json
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse
from fastapi import HTTPException, status
from app.services.chat_service import ChatService
from app.api.schemas import ChatMessageCreate
from app.db.models import User

logger = logging.getLogger(__name__)

class ChatController:
    @staticmethod
    async def chat(db: AsyncSession, current_user: User, chat_data: ChatMessageCreate) -> EventSourceResponse:
        """Controller to post a message and stream the assistant response via SSE."""
        # 1. Log the user's message in the DB (includes conversation ownership check)
        try:
            await ChatService.create_user_message(
                db=db,
                user_id=current_user.id,
                conversation_id=chat_data.conversation_id,
                content=chat_data.message
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e)
            )
        except Exception as e:
            logger.error(f"Error logging user message: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save message to database."
            )

        # 2. Define the generator that yields SSE formatted event payloads
        async def event_generator():
            try:
                # We yield messages token-by-token
                async for chunk in ChatService.stream_chat_response(
                    db=db,
                    user_id=current_user.id,
                    conversation_id=chat_data.conversation_id,
                    model_type=chat_data.model_type
                ):
                    yield {
                        "event": chunk["type"],  # 'delta', 'done', or 'error'
                        "data": json.dumps(chunk)
                    }
            except Exception as e:
                logger.error(f"Error in SSE streaming: {e}")
                yield {
                    "event": "error",
                    "data": json.dumps({"type": "error", "content": "Internal server streaming error."})
                }

        # 3. Return the SSE response
        return EventSourceResponse(event_generator())
