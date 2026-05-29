"""GDPR Compliance API Routes — data export and deletion endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.limiter import limiter
from app.api.dependencies import get_current_user
from app.api.controllers.gdpr_controller import GDPRController
from app.db.models import User
from pydantic import BaseModel

router = APIRouter(prefix="/gdpr", tags=["GDPR Compliance"])


class DeleteRequest(BaseModel):
    """Request body for GDPR data deletion — requires password confirmation."""
    password: str


@router.get("/export")
async def export_user_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export all personal data for the authenticated user.

    Complies with GDPR Article 15 (Right of access).
    Returns all personal data in a structured JSON format.
    """
    return await GDPRController.export_user_data(db, current_user)


@router.post("/delete")
async def delete_user_data(
    body: DeleteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Permanently delete or anonymize all personal data.

    Complies with GDPR Article 17 (Right to erasure).
    Requires password confirmation for security.
    After successful deletion, the user should log out.
    """
    return await GDPRController.delete_user_data(db, current_user, body.password)
