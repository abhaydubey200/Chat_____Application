import uuid
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.api.schemas import ConversationCreate, ConversationUpdate, ConversationResponse, ConversationDetailResponse
from app.api.controllers.conversation_controller import ConversationController
from app.db.models import User

router = APIRouter(prefix="/conversations", tags=["Conversations"])

@router.post("", response_model=ConversationResponse)
async def create_conversation(
    create_data: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new chat conversation."""
    return await ConversationController.create(db, current_user.id, create_data, current_user.organization_id)

@router.get("", response_model=List[ConversationResponse])
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve all conversations for the authenticated user."""
    return await ConversationController.list_conversations(db, current_user.id)

@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Fetch details and full history of a specific conversation."""
    return await ConversationController.get_conversation_detail(db, current_user.id, conversation_id)

@router.patch("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: uuid.UUID,
    update_data: ConversationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Rename a conversation's title."""
    return await ConversationController.update_conversation(db, current_user.id, conversation_id, update_data)

@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a conversation and all its messages."""
    return await ConversationController.delete_conversation(db, current_user.id, conversation_id)
