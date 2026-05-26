from sqlalchemy.ext.asyncio import AsyncSession
from app.services.admin_service import AdminService


class AdminController:
    @staticmethod
    async def analytics(db: AsyncSession) -> dict:
        return await AdminService.get_analytics(db)
