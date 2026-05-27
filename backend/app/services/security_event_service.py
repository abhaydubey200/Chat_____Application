import uuid
from datetime import datetime, timedelta
from typing import Any
from sqlalchemy import select, func
from app.core.database import AsyncSessionLocal
from app.core.observability import get_request_context
from app.db.models import SecurityEvent

class SecurityEventService:
    @staticmethod
    async def record_event(
        event_type: str,
        severity: str = "medium",
        status: str = "open",
        user_id: uuid.UUID | None = None,
        organization_id: uuid.UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        ctx = get_request_context()
        async with AsyncSessionLocal() as session:
            event = SecurityEvent(
                request_id=ctx.request_id if ctx else None,
                session_id=ctx.session_id if ctx else None,
                user_id=user_id,
                organization_id=organization_id,
                event_type=event_type,
                severity=severity,
                status=status,
                ip_address=ip_address or (ctx.client_ip if ctx else None),
                user_agent=user_agent,
                meta_data=metadata or {},
            )
            session.add(event)
            await session.commit()

    @staticmethod
    async def recent_failed_logins(ip_address: str | None, window_minutes: int = 10) -> int:
        if not ip_address:
            return 0
        cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
        async with AsyncSessionLocal() as session:
            stmt = select(func.count()).select_from(SecurityEvent).where(
                SecurityEvent.event_type == "auth_failed_login",
                SecurityEvent.ip_address == ip_address,
                SecurityEvent.created_at >= cutoff,
            )
            result = await session.execute(stmt)
            return int(result.scalar() or 0)
