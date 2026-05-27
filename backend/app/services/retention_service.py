import asyncio
from datetime import datetime, timedelta
from sqlalchemy import select, update, delete, text
from app.core.database import AsyncSessionLocal
from app.core.config import settings
from app.core.observability import get_logger
from app.db.models import RetentionPolicy, RetentionJob, Conversation, Message, AuditLog, UsageEvent, DlpEvent, SecurityEvent

logger = get_logger(__name__)

class RetentionService:
    _task: asyncio.Task | None = None

    @staticmethod
    async def run_once() -> None:
        async with AsyncSessionLocal() as session:
            policies_result = await session.execute(
                select(RetentionPolicy).where(RetentionPolicy.is_active.is_(True))
            )
            policies = list(policies_result.scalars().all())
            if not policies:
                return

            for policy in policies:
                job = RetentionJob(organization_id=policy.organization_id)
                session.add(job)
                await session.flush()

                total_affected = 0
                now = datetime.utcnow()

                if policy.data_type in {"conversations", "messages"}:
                    soft_days = policy.soft_delete_after_days or settings.RETENTION_DEFAULT_SOFT_DELETE_DAYS
                    hard_days = policy.hard_delete_after_days or settings.RETENTION_DEFAULT_HARD_DELETE_DAYS

                    soft_cutoff = now - timedelta(days=soft_days)
                    hard_cutoff = now - timedelta(days=hard_days)

                    if policy.data_type == "conversations":
                        soft_stmt = update(Conversation).where(
                            Conversation.organization_id == policy.organization_id,
                            Conversation.deleted_at.is_(None),
                            Conversation.created_at < soft_cutoff,
                        ).values(deleted_at=now)
                        result = await session.execute(soft_stmt)
                        total_affected += result.rowcount or 0

                        hard_stmt = delete(Conversation).where(
                            Conversation.organization_id == policy.organization_id,
                            Conversation.deleted_at.is_not(None),
                            Conversation.deleted_at < hard_cutoff,
                        )
                        result = await session.execute(hard_stmt)
                        total_affected += result.rowcount or 0

                    if policy.data_type == "messages":
                        soft_stmt = update(Message).where(
                            Message.conversation_id.in_(
                                select(Conversation.id).where(
                                    Conversation.organization_id == policy.organization_id
                                )
                            ),
                            Message.deleted_at.is_(None),
                            Message.created_at < soft_cutoff,
                        ).values(deleted_at=now)
                        result = await session.execute(soft_stmt)
                        total_affected += result.rowcount or 0

                        hard_stmt = delete(Message).where(
                            Message.deleted_at.is_not(None),
                            Message.deleted_at < hard_cutoff,
                        )
                        result = await session.execute(hard_stmt)
                        total_affected += result.rowcount or 0

                if policy.data_type in {"audit", "usage", "dlp", "security"}:
                    hard_days = policy.hard_delete_after_days or settings.RETENTION_DEFAULT_HARD_DELETE_DAYS
                    hard_cutoff = now - timedelta(days=hard_days)
                    await session.execute(text("SET LOCAL governance.allow_delete = 'true'"))

                    table_map = {
                        "audit": AuditLog,
                        "usage": UsageEvent,
                        "dlp": DlpEvent,
                        "security": SecurityEvent,
                    }
                    model = table_map.get(policy.data_type)
                    if model:
                        delete_stmt = delete(model).where(
                            model.organization_id == policy.organization_id,
                            model.created_at < hard_cutoff,
                        )
                        result = await session.execute(delete_stmt)
                        total_affected += result.rowcount or 0

                job.records_affected = total_affected
                job.status = "completed"
                job.finished_at = datetime.utcnow()

            await session.commit()

    @staticmethod
    def start_scheduler() -> None:
        if RetentionService._task and not RetentionService._task.done():
            return

        async def _loop():
            while True:
                try:
                    await RetentionService.run_once()
                except Exception as exc:
                    logger.error(
                        "Retention job failed",
                        extra={"event_type": "retention_error", "error_type": type(exc).__name__},
                        exc_info=True,
                    )
                await asyncio.sleep(settings.RETENTION_JOB_INTERVAL_MINUTES * 60)

        RetentionService._task = asyncio.create_task(_loop())

    @staticmethod
    async def stop_scheduler() -> None:
        if RetentionService._task:
            RetentionService._task.cancel()
            RetentionService._task = None
