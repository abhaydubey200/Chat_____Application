import uuid
from datetime import datetime
from typing import Any
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from app.core.database import AsyncSessionLocal
from app.core.observability import get_request_context, get_stream_context, get_logger
from app.db.models import UsageEvent, UsageDailyAggregate, ModelPolicy

logger = get_logger(__name__)

try:
    import tiktoken
except Exception:  # pragma: no cover - optional dependency
    tiktoken = None

class TokenEstimator:
    _encoding_cache: dict[str, Any] = {}

    @staticmethod
    def _get_encoding(model: str):
        if not tiktoken:
            return None
        if model in TokenEstimator._encoding_cache:
            return TokenEstimator._encoding_cache[model]
        try:
            encoding = tiktoken.encoding_for_model(model)
        except Exception:
            encoding = tiktoken.get_encoding("cl100k_base")
        TokenEstimator._encoding_cache[model] = encoding
        return encoding

    @staticmethod
    def estimate_text_tokens(text: str, model: str | None = None) -> int:
        if not text:
            return 0
        encoding = TokenEstimator._get_encoding(model or "cl100k_base")
        if encoding:
            return len(encoding.encode(text))
        return max(1, int(len(text.split()) * 1.3))

    @staticmethod
    def estimate_messages_tokens(messages: list[dict], model: str | None = None) -> int:
        combined = "\n".join(f"{m.get('role', '')}: {m.get('content', '')}" for m in messages)
        return TokenEstimator.estimate_text_tokens(combined, model=model)

class UsageService:
    @staticmethod
    async def get_model_pricing(
        organization_id: uuid.UUID | None,
        provider_name: str,
        model_name: str,
    ) -> tuple[float, float]:
        if not organization_id:
            return 0.0, 0.0
        async with AsyncSessionLocal() as session:
            stmt = select(ModelPolicy).where(
                ModelPolicy.organization_id == organization_id,
                ModelPolicy.provider_name == provider_name,
                ModelPolicy.model_name == model_name,
                ModelPolicy.is_enabled.is_(True),
            )
            result = await session.execute(stmt)
            policy = result.scalar_one_or_none()
            if not policy:
                return 0.0, 0.0
            return float(policy.cost_per_1k_input), float(policy.cost_per_1k_output)

    @staticmethod
    def estimate_cost(input_tokens: int, output_tokens: int, cost_in: float, cost_out: float) -> float:
        return round((input_tokens / 1000.0) * cost_in + (output_tokens / 1000.0) * cost_out, 6)

    @staticmethod
    async def record_usage(
        user_id: uuid.UUID | None,
        organization_id: uuid.UUID | None,
        conversation_id: uuid.UUID | None,
        provider_name: str,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: int | None,
        stream_duration_ms: int | None,
        retry_count: int = 0,
        status: str = "success",
        metadata: dict | None = None,
    ) -> None:
        ctx = get_request_context()
        stream_ctx = get_stream_context()
        cost_in, cost_out = await UsageService.get_model_pricing(organization_id, provider_name, model_name)
        total_tokens = input_tokens + output_tokens
        cost_usd = UsageService.estimate_cost(input_tokens, output_tokens, cost_in, cost_out)

        async with AsyncSessionLocal() as session:
            event = UsageEvent(
                request_id=ctx.request_id if ctx else None,
                session_id=ctx.session_id if ctx else None,
                user_id=user_id,
                organization_id=organization_id,
                conversation_id=conversation_id,
                provider_name=provider_name,
                model_name=model_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                cost_usd=cost_usd,
                latency_ms=latency_ms,
                stream_duration_ms=stream_duration_ms,
                retry_count=retry_count,
                status=status,
                meta_data=metadata or {},
            )
            session.add(event)

            usage_date = datetime.utcnow().date()
            aggregate_stmt = insert(UsageDailyAggregate).values(
                organization_id=organization_id,
                user_id=user_id,
                usage_date=usage_date,
                provider_name=provider_name,
                model_name=model_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                cost_usd=cost_usd,
                request_count=1,
                error_count=1 if status != "success" else 0,
            ).on_conflict_do_update(
                index_elements=["organization_id", "user_id", "usage_date", "provider_name", "model_name"],
                set_={
                    "input_tokens": UsageDailyAggregate.input_tokens + input_tokens,
                    "output_tokens": UsageDailyAggregate.output_tokens + output_tokens,
                    "total_tokens": UsageDailyAggregate.total_tokens + total_tokens,
                    "cost_usd": UsageDailyAggregate.cost_usd + cost_usd,
                    "request_count": UsageDailyAggregate.request_count + 1,
                    "error_count": UsageDailyAggregate.error_count + (1 if status != "success" else 0),
                },
            )
            await session.execute(aggregate_stmt)
            await session.commit()

        if stream_ctx:
            stream_ctx.input_tokens = input_tokens
            stream_ctx.output_tokens = output_tokens
            stream_ctx.total_tokens = total_tokens
