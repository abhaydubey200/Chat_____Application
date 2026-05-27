import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Organization

class OrganizationRepository:
    @staticmethod
    async def create(db: AsyncSession, name: str) -> Organization:
        organization = Organization(name=name)
        db.add(organization)
        await db.flush()
        return organization

    @staticmethod
    async def get_by_id(db: AsyncSession, organization_id: uuid.UUID) -> Organization | None:
        stmt = select(Organization).where(Organization.id == organization_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
