import json
import asyncio
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse
from fastapi import HTTPException, status, Request
from app.services.chat_service import ChatService
from app.services.audit_service import AuditService
from app.services.dlp_service import DlpService
from app.services.security_event_service import SecurityEventService
from app.api.schemas import ChatMessageCreate
from app.db.models import User
from app.core.database import AsyncSessionLocal
from app.core.observability import (
    get_logger,
    StreamContext,
    RequestContext,
    get_request_context,
    set_stream_context,
    get_stream_context,
    get_metrics,
)
from app.core.observability.error_types import (
    StreamLifecycleError,
    RequestValidationError,
    get_error_category,
)

logger = get_logger(__name__)

class ChatController:
    @staticmethod
    async def chat(
        db: AsyncSession,
        current_user: User,
        chat_data: ChatMessageCreate,
        request: Request,
    ) -> EventSourceResponse:
        """Handle chat streaming with comprehensive observability and lifecycle tracking.

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
        # Get request context and update with user info
        req_ctx = get_request_context()
        if req_ctx:
            req_ctx.user_id = str(current_user.id)
            req_ctx.conversation_id = str(chat_data.conversation_id)
            if current_user.organization_id:
                req_ctx.organization_id = str(current_user.organization_id)
        
        # Create stream context for lifecycle tracking
        stream_id = str(uuid.uuid4())
        stream_ctx = StreamContext(
            stream_id=stream_id,
            request_id=req_ctx.request_id if req_ctx else str(uuid.uuid4()),
            user_id=str(current_user.id),
            conversation_id=str(chat_data.conversation_id),
            model_type=chat_data.model_type,
            stream_start_time=datetime.now(timezone.utc),
        )
        set_stream_context(stream_ctx)
        
        metrics = get_metrics()
        metrics.increment_active_streams(1)
        metrics.increment_total_requests()
        
        logger.log_stream_start(
            stream_id=stream_id,
            model_type=chat_data.model_type,
            provider_name="unknown",  # Will be updated when provider is selected
        )
        
        # 1. Run DLP scan before persistence/provider calls
        dlp_result = await DlpService.scan_prompt(chat_data.message)
        if dlp_result.matches:
            await DlpService.record_event(
                dlp_result,
                user_id=current_user.id,
                organization_id=current_user.organization_id,
                conversation_id=chat_data.conversation_id,
            )
            AuditService.append_background(
                event_type=f"dlp_{dlp_result.action}",
                status="success" if dlp_result.action in {"warn", "allow"} else "blocked",
                user_id=current_user.id,
                organization_id=current_user.organization_id,
                conversation_id=chat_data.conversation_id,
                metadata={"match_count": len(dlp_result.matches)},
            )
            if dlp_result.action == "block":
                await SecurityEventService.record_event(
                    event_type="dlp_block",
                    severity="high",
                    user_id=current_user.id,
                    organization_id=current_user.organization_id,
                    metadata={"conversation_id": str(chat_data.conversation_id)},
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Message blocked by DLP policy.",
                )
            if dlp_result.action == "escalate":
                await SecurityEventService.record_event(
                    event_type="dlp_escalation",
                    severity="medium",
                    user_id=current_user.id,
                    organization_id=current_user.organization_id,
                    metadata={"conversation_id": str(chat_data.conversation_id)},
                )

        # 2. Validate and save user's message to database
        try:
            await ChatService.create_user_message(
                db=db,
                user_id=current_user.id,
                conversation_id=chat_data.conversation_id,
                content=chat_data.message,
            )
            AuditService.append_background(
                event_type="message_submitted",
                status="success",
                user_id=current_user.id,
                organization_id=current_user.organization_id,
                conversation_id=chat_data.conversation_id,
                metadata={"message_length": len(chat_data.message)},
            )
            logger.debug(
                "User message saved",
                extra={
                    "event_type": "user_message_saved",
                    "message_length": len(chat_data.message),
                },
            )

        except ValueError as e:
            logger.warning(
                "Validation error saving message",
                extra={
                    "event_type": "message_validation_error",
                    "error": str(e),
                    "error_category": "request_validation",
                },
            )
            stream_ctx.completion_reason = "error"
            stream_ctx.stream_error = "Invalid request"
            metrics.increment_active_streams(-1)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e),
            )
        except Exception as e:
            error_category = get_error_category(e)
            logger.error(
                "Error saving user message",
                extra={
                    "event_type": "message_save_error",
                    "error_type": type(e).__name__,
                    "error_category": error_category.value,
                },
                exc_info=True,
            )
            stream_ctx.completion_reason = "error"
            stream_ctx.stream_error = "Failed to save message"
            metrics.increment_active_streams(-1)
            metrics.increment_failed_requests()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save your message. Please try again.",
            )

        # 3. Define SSE event generator with comprehensive observability
        async def event_generator():
            """Generate SSE events for streaming chat response with lifecycle tracking.

            Handles:
            - Token-by-token streaming with chunk counting
            - Stream lifecycle events (start, progress, completion)
            - Error propagation with categorization
            - Client disconnection detection
            - Proper session cleanup on cancellation
            """
            chunk_count = 0
            stream_start = datetime.now(timezone.utc)
            first_token_received = False
            
            async with AsyncSessionLocal() as stream_db:
                try:
                    async for chunk in ChatService.stream_chat_response(
                        db=stream_db,
                        user_id=current_user.id,
                        conversation_id=chat_data.conversation_id,
                        model_type=chat_data.model_type,
                        organization_id=current_user.organization_id,
                    ):
                        if await request.is_disconnected():
                            logger.warning(
                                "Client disconnected during stream",
                                extra={
                                    "event_type": "stream_cancelled",
                                    "chunks_sent": chunk_count,
                                },
                            )
                            stream_ctx.completion_reason = "cancelled"
                            AuditService.append_background(
                                event_type="stream_cancelled",
                                status="success",
                                user_id=current_user.id,
                                organization_id=current_user.organization_id,
                                conversation_id=chat_data.conversation_id,
                                metadata={"chunks_sent": chunk_count},
                            )
                            break

                        # Track first token for latency measurement
                        if not first_token_received and chunk.get("type") == "delta":
                            first_token_received = True
                            stream_ctx.first_token_time = datetime.now(timezone.utc)
                            logger.debug(
                                "First token received",
                                extra={
                                    "event_type": "first_token",
                                    "latency_ms": stream_ctx.first_token_latency_ms(),
                                },
                            )

                        chunk_count += 1
                        stream_ctx.chunk_count = chunk_count
                        
                        # Update provider info from chunk metadata
                        if chunk.get("provider"):
                            stream_ctx.provider_name = chunk.get("provider")
                        if chunk.get("model"):
                            stream_ctx.model_name = chunk.get("model")

                        # Log streaming progress periodically
                        if chunk_count % 100 == 0:
                            logger.debug(
                                "Streaming progress",
                                extra={
                                    "event_type": "stream_progress",
                                    "chunks_sent": chunk_count,
                                },
                            )

                        yield {
                            "event": chunk["type"],  # 'delta', 'done', or 'error'
                            "data": json.dumps(chunk),
                        }
                        
                        # Mark stream as completed if this is the final event
                        if chunk.get("type") == "done":
                            stream_ctx.completion_reason = "completed"
                        elif chunk.get("type") == "error":
                            stream_ctx.completion_reason = "error"
                            stream_ctx.stream_error = chunk.get("content", "Unknown error")

                    logger.info(
                        "Stream completed successfully",
                        extra={
                            "event_type": "stream_completed",
                            "total_chunks": chunk_count,
                            "duration_ms": (datetime.now(timezone.utc) - stream_start).total_seconds() * 1000,
                        },
                    )

                except asyncio.CancelledError:
                    logger.info(
                        "Stream cancelled by client",
                        extra={
                            "event_type": "stream_cancelled",
                            "chunks_sent": chunk_count,
                        },
                    )
                    stream_ctx.completion_reason = "cancelled"
                    await stream_db.rollback()
                    raise
                    
                except Exception as e:
                    error_category = get_error_category(e)
                    await stream_db.rollback()
                    logger.error(
                        "Error during stream",
                        extra={
                            "event_type": "stream_error",
                            "error_type": type(e).__name__,
                            "error_category": error_category.value,
                            "chunks_sent": chunk_count,
                        },
                        exc_info=True,
                    )
                    stream_ctx.completion_reason = "error"
                    stream_ctx.stream_error = str(e)
                    metrics.increment_failed_requests()
                    AuditService.append_background(
                        event_type="stream_error",
                        status="error",
                        user_id=current_user.id,
                        organization_id=current_user.organization_id,
                        conversation_id=chat_data.conversation_id,
                        metadata={"error_type": type(e).__name__},
                    )

                    yield {
                        "event": "error",
                        "data": json.dumps({
                            "type": "error",
                            "content": "An error occurred while processing your request. Please try again.",
                        }),
                    }
                finally:
                    # Update stream context with final metrics
                    stream_ctx.stream_end_time = datetime.now(timezone.utc)
                    
                    # Log stream lifecycle completion
                    logger.log_stream_end(
                        stream_id=stream_id,
                        completion_reason=stream_ctx.completion_reason,
                        duration_ms=stream_ctx.stream_duration_ms() or 0,
                        tokens_generated=stream_ctx.chunk_count,
                    )
                    
                    # Decrement active stream count
                    metrics.increment_active_streams(-1)

        # 3. Return SSE response with appropriate headers
        return EventSourceResponse(
            event_generator(),
            media_type="text/event-stream",
        )
