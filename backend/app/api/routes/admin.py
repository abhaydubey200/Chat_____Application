from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.dependencies import require_admin
from app.api.schemas import AdminAnalyticsResponse
from app.api.controllers.admin_controller import AdminController
from app.db.models import User

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/analytics", response_model=AdminAnalyticsResponse)
async def get_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Retrieve admin analytics dashboard metrics."""
    return await AdminController.analytics(db)
