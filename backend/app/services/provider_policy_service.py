import uuid
from sqlalchemy import select, func
from app.core.database import AsyncSessionLocal
from app.db.models import ProviderPolicy, ModelPolicy, UsageDailyAggregate
from app.core.time import utc_now

class ProviderPolicyService:
    @staticmethod
    async def get_provider_policy(organization_id: uuid.UUID, provider_name: str) -> ProviderPolicy | None:
        async with AsyncSessionLocal() as session:
            stmt = select(ProviderPolicy).where(
                ProviderPolicy.organization_id == organization_id,
                ProviderPolicy.provider_name == provider_name,
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    @staticmethod
    async def get_model_policy(
        organization_id: uuid.UUID,
        provider_name: str,
        model_name: str,
    ) -> ModelPolicy | None:
        async with AsyncSessionLocal() as session:
            stmt = select(ModelPolicy).where(
                ModelPolicy.organization_id == organization_id,
                ModelPolicy.provider_name == provider_name,
                ModelPolicy.model_name == model_name,
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    @staticmethod
    async def daily_cost_for_provider(organization_id: uuid.UUID, provider_name: str) -> float:
        today = utc_now().date()
        async with AsyncSessionLocal() as session:
            stmt = select(func.coalesce(func.sum(UsageDailyAggregate.cost_usd), 0)).where(
                UsageDailyAggregate.organization_id == organization_id,
                UsageDailyAggregate.provider_name == provider_name,
                UsageDailyAggregate.usage_date == today,
            )
            result = await session.execute(stmt)
            return float(result.scalar() or 0)

    @staticmethod
    async def validate_provider_usage(
        organization_id: uuid.UUID,
        provider_name: str,
        model_name: str,
        model_type: str,
        estimated_request_cost: float | None = None,
    ) -> tuple[bool, str | None]:
        provider_policy = await ProviderPolicyService.get_provider_policy(organization_id, provider_name)
        if provider_policy and not provider_policy.is_enabled:
            return False, f"Provider '{provider_name}' is disabled by policy."
        if provider_policy and not provider_policy.allow_reasoning and model_type == "reasoning":
            return False, "Reasoning models are disabled by policy."

        model_policy = await ProviderPolicyService.get_model_policy(organization_id, provider_name, model_name)
        if model_policy and not model_policy.is_enabled:
            return False, f"Model '{model_name}' is disabled by policy."

        if provider_policy and provider_policy.max_cost_usd_per_request and estimated_request_cost is not None:
            if estimated_request_cost > float(provider_policy.max_cost_usd_per_request):
                return False, "Request cost exceeds policy limit."

        if provider_policy and provider_policy.max_cost_usd_per_day:
            daily_cost = await ProviderPolicyService.daily_cost_for_provider(organization_id, provider_name)
            if daily_cost >= float(provider_policy.max_cost_usd_per_day):
                return False, "Daily cost ceiling reached for provider."

        return True, None
