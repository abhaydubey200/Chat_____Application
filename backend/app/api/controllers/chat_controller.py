import json
import logging
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse
from fastapi import HTTPException, status, Request
from app.services.chat_service import ChatService
from app.api.schemas import ChatMessageCreate
from app.db.models import User
from app.core.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

class ChatController:
    @staticmethod
    async def chat(
        db: AsyncSession,
        current_user: User,
        chat_data: ChatMessageCreate,
        request: Request,
    ) -> EventSourceResponse:
        """Handle chat streaming with proper error handling and client disconnect detection.

        Args:
            db: Database session (used only for initial message persistence)
            current_user: Authenticated user
            chat_data: Request data with conversation_id, message, model_type
            request: FastAPI request object (for disconnect detection)

        Returns:
            EventSourceResponse: SSE stream of chat tokens

        Raises:
            HTTPException: If message save or streaming fails
        """
        # 1. Validate and save user's message to database
        try:
            await ChatService.create_user_message(
                db=db,
                user_id=current_user.id,
                conversation_id=chat_data.conversation_id,
                content=chat_data.message,
            )
            logger.debug(
                "User message saved",
                extra={"conversation_id": str(chat_data.conversation_id)},
            )

        except ValueError as e:
            logger.warning(
                "Validation error saving message",
                extra={"error": str(e)},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e),
            )
        except Exception as e:
            logger.error(
                "Error saving user message",
                extra={"error_type": type(e).__name__},
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save your message. Please try again.",
            )

        # 2. Define SSE event generator with cancellation support
        #    Uses its own DB session for streaming to avoid holding the
        #    middleware session open for the entire stream duration.
        async def event_generator():
            """Generate SSE events for streaming chat response.

            Handles:
            - Token-by-token streaming
            - Error propagation and recovery
            - Client disconnection detection
            - Proper session cleanup on cancellation
            """
            chunk_count = 0
            async with AsyncSessionLocal() as stream_db:
                try:
                    async for chunk in ChatService.stream_chat_response(
                        db=stream_db,
                        user_id=current_user.id,
                        conversation_id=chat_data.conversation_id,
                        model_type=chat_data.model_type,
                    ):
                        if await request.is_disconnected():
                            logger.info(
                                "Client disconnected during stream",
                                extra={
                                    "conversation_id": str(chat_data.conversation_id),
                                    "chunks_sent": chunk_count,
                                },
                            )
                            break

                        chunk_count += 1

                        # Log streaming progress periodically
                        if chunk_count % 50 == 0:
                            logger.debug(
                                "Streaming progress",
                                extra={
                                    "conversation_id": str(chat_data.conversation_id),
                                    "chunks_sent": chunk_count,
                                },
                            )

                        yield {
                            "event": chunk["type"],  # 'delta', 'done', or 'error'
                            "data": json.dumps(chunk),
                        }

                    logger.debug(
                        "Stream completed",
                        extra={
                            "conversation_id": str(chat_data.conversation_id),
                            "total_chunks": chunk_count,
                        },
                    )

                except asyncio.CancelledError:
                    logger.info(
                        "Stream cancelled by client",
                        extra={
                            "conversation_id": str(chat_data.conversation_id),
                            "chunks_sent": chunk_count,
                        },
                    )
                    # Rollback any pending transaction in the stream session
                    await stream_db.rollback()
                    raise
                except Exception as e:
                    await stream_db.rollback()
                    logger.error(
                        "Error during stream",
                        extra={
                            "conversation_id": str(chat_data.conversation_id),
                            "error_type": type(e).__name__,
                            "chunks_sent": chunk_count,
                        },
                        exc_info=True,
                    )

                    yield {
                        "event": "error",
                        "data": json.dumps({
                            "type": "error",
                            "content": "An error occurred while processing your request. Please try again.",
                        }),
                    }

        # 3. Return SSE response with appropriate headers
        return EventSourceResponse(
            event_generator(),
            media_type="text/event-stream",
        )
