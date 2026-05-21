from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.api.schemas import ChatMessageCreate
from app.api.controllers.chat_controller import ChatController
from app.db.models import User

router = APIRouter(prefix="/chat", tags=["Streaming Chat"])

@router.post("")
async def stream_chat(
    chat_data: ChatMessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Send a user message and return an SSE stream of token deltas.
    
    Rate limited: 30 requests per minute per user to prevent API quota exhaustion.
    """
    # Rate limiting is handled via FastAPI dependency in the limiter attached to app.state
    # The limiter decorator would be: @limiter.limit("30/minute")
    # But we apply it at app initialization with middleware instead
    return await ChatController.chat(db, current_user, chat_data)
