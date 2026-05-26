from datetime import datetime, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core import security
from app.db.models import User, Conversation, Message
from app.db.repositories.user_repository import UserRepository


class AdminService:
    @staticmethod
    async def ensure_admin_user(db: AsyncSession) -> User | None:
        if not settings.ADMIN_EMAIL or not settings.ADMIN_PASSWORD:
            return None

        existing = await UserRepository.get_by_email(db, settings.ADMIN_EMAIL)
        if existing:
            if existing.priority != settings.ADMIN_PRIORITY:
                existing.priority = settings.ADMIN_PRIORITY
                db.add(existing)
                await db.commit()
                await db.refresh(existing)
            return existing

        password_hash = security.get_password_hash(settings.ADMIN_PASSWORD)
        user = await UserRepository.create(
            db=db,
            email=settings.ADMIN_EMAIL,
            password_hash=password_hash,
            priority=settings.ADMIN_PRIORITY
        )
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def get_analytics(db: AsyncSession) -> dict:
        total_users = await db.scalar(select(func.count(User.id)))
        total_chats = await db.scalar(select(func.count(Conversation.id)))

        provider_rows = await db.execute(
            select(Message.provider_used, func.count(Message.id))
            .where(Message.role == "assistant", Message.provider_used.is_not(None))
            .group_by(Message.provider_used)
            .order_by(func.count(Message.id).desc())
        )
        provider_usage = [
            {"label": provider, "count": count}
            for provider, count in provider_rows.all()
        ]

        model_rows = await db.execute(
            select(Message.model_used, func.count(Message.id))
            .where(Message.role == "assistant", Message.model_used.is_not(None))
            .group_by(Message.model_used)
            .order_by(func.count(Message.id).desc())
        )
        model_usage = [
            {"label": model, "count": count}
            for model, count in model_rows.all()
        ]

        start_date = datetime.utcnow().date() - timedelta(days=29)
        daily_rows = await db.execute(
            select(func.date(Message.created_at), func.count(Message.id))
            .where(Message.role == "user", Message.created_at >= start_date)
            .group_by(func.date(Message.created_at))
            .order_by(func.date(Message.created_at))
        )
        daily_map = {day: count for day, count in daily_rows.all()}
        daily_requests = []
        for offset in range(30):
            day = start_date + timedelta(days=offset)
            daily_requests.append({
                "date": day.isoformat(),
                "count": int(daily_map.get(day, 0))
            })

        return {
            "total_users": int(total_users or 0),
            "total_chats": int(total_chats or 0),
            "provider_usage": provider_usage,
            "model_usage": model_usage,
            "daily_requests": daily_requests
        }
