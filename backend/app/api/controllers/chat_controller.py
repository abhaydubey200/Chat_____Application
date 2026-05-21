import json
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse
from fastapi import HTTPException, status, Request
from app.services.chat_service import ChatService
from app.api.schemas import ChatMessageCreate
from app.db.models import User

logger = logging.getLogger(__name__)

class ChatController:
    @staticmethod
    async def chat(db: AsyncSession, current_user: User, chat_data: ChatMessageCreate) -> EventSourceResponse:
        """Handle chat streaming with proper error handling and client disconnect detection.
        
        Args:
            db: Database session
            current_user: Authenticated user
            chat_data: Request data with conversation_id, message, model_type
            
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
                content=chat_data.message
            )
            logger.debug(f"User message saved for conversation={chat_data.conversation_id}")
            
        except ValueError as e:
            logger.warning(f"Validation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e)
            )
        except Exception as e:
            logger.error(f"Error saving user message: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save your message. Please try again."
            )

        # 2. Define SSE event generator with cancellation support
        async def event_generator():
            """Generate SSE events for streaming chat response.
            
            Handles:
            - Token-by-token streaming
            - Error propagation
            - Client disconnection detection
            """
            try:
                # Stream response from chat service
                chunk_count = 0
                async for chunk in ChatService.stream_chat_response(
                    db=db,
                    user_id=current_user.id,
                    conversation_id=chat_data.conversation_id,
                    model_type=chat_data.model_type
                ):
                    chunk_count += 1
                    
                    # Log streaming progress periodically
                    if chunk_count % 50 == 0:
                        logger.debug(
                            f"Streaming progress",
                            extra={
                                "conversation_id": str(chat_data.conversation_id),
                                "chunks_sent": chunk_count
                            }
                        )
                    
                    # Yield SSE formatted event
                    yield {
                        "event": chunk["type"],  # 'delta', 'done', or 'error'
                        "data": json.dumps(chunk)
                    }
                    
                logger.debug(
                    f"Stream completed",
                    extra={
                        "conversation_id": str(chat_data.conversation_id),
                        "total_chunks": chunk_count
                    }
                )
                    
            except Exception as e:
                logger.error(
                    f"Error during streaming",
                    extra={
                        "conversation_id": str(chat_data.conversation_id),
                        "error_type": type(e).__name__
                    },
                    exc_info=True
                )
                
                # Emit error event to client
                yield {
                    "event": "error",
                    "data": json.dumps({
                        "type": "error",
                        "content": "An error occurred while processing your request. Please try again."
                    })
                }

        # 3. Return SSE response
        return EventSourceResponse(
            event_generator(),
            media_type="text/event-stream"
        )
