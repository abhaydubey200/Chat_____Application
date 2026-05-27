import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import OrgMembership

class OrgMembershipRepository:
    @staticmethod
    async def create(
        db: AsyncSession,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        role: str,
    ) -> OrgMembership:
        membership = OrgMembership(
            organization_id=organization_id,
            user_id=user_id,
            role=role,
        )
        db.add(membership)
        await db.flush()
        return membership

    @staticmethod
    async def get_by_user_and_org(
        db: AsyncSession,
        user_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> OrgMembership | None:
        stmt = select(OrgMembership).where(
            OrgMembership.user_id == user_id,
            OrgMembership.organization_id == organization_id,
            OrgMembership.is_active.is_(True),
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
