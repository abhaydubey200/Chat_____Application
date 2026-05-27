import asyncio
import uuid
from typing import Any
from app.core.database import AsyncSessionLocal
from app.core.observability import get_request_context, get_stream_context, get_logger
from app.core.observability.structured_logger import SensitiveDataRedactor
from app.core.config import settings
from app.db.models import AuditLog

logger = get_logger(__name__)

def _to_uuid(value: str | uuid.UUID | None) -> uuid.UUID | None:
    if value is None or isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except ValueError:
        return None

class AuditService:
    @staticmethod
    async def append(
        event_type: str,
        status: str = "success",
        user_id: str | uuid.UUID | None = None,
        organization_id: str | uuid.UUID | None = None,
        conversation_id: str | uuid.UUID | None = None,
        provider_name: str | None = None,
        model_name: str | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        latency_ms: int | None = None,
        metadata: dict[str, Any] | None = None,
        request_id: str | None = None,
        session_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        req_ctx = get_request_context()
        stream_ctx = get_stream_context()

        request_id = request_id or (req_ctx.request_id if req_ctx else None)
        session_id = session_id or (req_ctx.session_id if req_ctx else None)
        user_id = user_id or (req_ctx.user_id if req_ctx else None)
        organization_id = organization_id or (req_ctx.organization_id if req_ctx else None)
        conversation_id = conversation_id or (req_ctx.conversation_id if req_ctx else None)
        provider_name = provider_name or (stream_ctx.provider_name if stream_ctx else None)
        model_name = model_name or (stream_ctx.model_name if stream_ctx else None)

        safe_metadata = metadata or {}
        if settings.AUDIT_REDACT_CONTENT:
            safe_metadata = SensitiveDataRedactor.redact_dict(safe_metadata)

        log = AuditLog(
            request_id=request_id,
            session_id=session_id,
            user_id=_to_uuid(user_id),
            organization_id=_to_uuid(organization_id),
            conversation_id=_to_uuid(conversation_id),
            event_type=event_type,
            status=status,
            provider_name=provider_name,
            model_name=model_name,
            ip_address=ip_address or (req_ctx.client_ip if req_ctx else None),
            user_agent=user_agent or (req_ctx.user_agent if req_ctx else None),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            meta_data=safe_metadata,
        )

        async with AsyncSessionLocal() as session:
            session.add(log)
            await session.commit()

    @staticmethod
    def append_background(**kwargs) -> None:
        async def _run():
            try:
                await AuditService.append(**kwargs)
            except Exception as exc:
                logger.error(
                    "Failed to append audit log",
                    extra={"event_type": "audit_log_error", "error_type": type(exc).__name__},
                    exc_info=True,
                )
        asyncio.create_task(_run())
