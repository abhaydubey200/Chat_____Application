import uuid
from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.api.controllers.admin_controller import AdminController
from app.db.models import User

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/dashboard")
async def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get comprehensive admin dashboard statistics."""
    return await AdminController.get_dashboard_summary(db, current_user)


@router.get("/users/{user_id}")
async def get_user_detail(
    user_id: uuid.UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get complete end-to-end tracking data for a specific user."""
    return await AdminController.get_user_detail(db, current_user, user_id, page=page, per_page=per_page)


@router.get("/conversations")
async def list_all_conversations(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
    search: str | None = Query(None, min_length=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all conversations across the system with user info."""
    return await AdminController.list_all_conversations(
        db, current_user, page=page, per_page=per_page, search=search
    )


@router.get("/conversations/{conversation_id}")
async def get_conversation_detail(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get full conversation detail with messages (admin view, any user's conversation)."""
    return await AdminController.get_conversation_detail(db, current_user, conversation_id)


@router.get("/audit")
async def list_audit_logs(
    page: int = Query(1, ge=1),
    per_page: int = Query(30, ge=1, le=100),
    status: str | None = Query(None),
    event_type: str | None = Query(None),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Paginated audit logs with filters."""
    return await AdminController.list_audit_logs(
        db, current_user, page=page, per_page=per_page,
        status=status, event_type=event_type,
        start_date=start_date, end_date=end_date,
    )


@router.get("/security")
async def list_security_events(
    page: int = Query(1, ge=1),
    per_page: int = Query(30, ge=1, le=100),
    severity: str | None = Query(None),
    status: str | None = Query(None),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Paginated security events with filters."""
    return await AdminController.list_security_events(
        db, current_user, page=page, per_page=per_page,
        severity=severity, status=status,
        start_date=start_date, end_date=end_date,
    )


@router.get("/dlp")
async def list_dlp_events(
    page: int = Query(1, ge=1),
    per_page: int = Query(30, ge=1, le=100),
    action: str | None = Query(None),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Paginated DLP events with filters."""
    return await AdminController.list_dlp_events(
        db, current_user, page=page, per_page=per_page,
        action=action,
        start_date=start_date, end_date=end_date,
    )
