import uuid
from datetime import date, timedelta
from typing import Any
from sqlalchemy import select, func, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import (
    User, OrgMembership, Conversation, Message,
    UsageEvent, AuditLog, SecurityEvent, DlpEvent,
    ProviderPolicy, ModelPolicy, Organization,
)
from app.core.rbac import ROLE_SUPER_ADMIN, ROLE_ADMIN, ROLE_SECURITY_ADMIN
from app.core.time import utc_now
from fastapi import HTTPException, status, Query
from sqlalchemy import text


def _serialize(val: Any) -> Any:
    """Convert common non-serializable types to native Python types."""
    if isinstance(val, uuid.UUID):
        return str(val)
    if isinstance(val, date):
        return val.isoformat()
    if isinstance(val, float):
        return round(val, 6)
    if hasattr(val, 'isoformat'):
        return val.isoformat()
    return val


async def _verify_admin(db: AsyncSession, current_user: User) -> None:
    """Verify user has admin-level role."""
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to access this resource."
        )
    stmt = select(OrgMembership).where(
        OrgMembership.user_id == current_user.id,
        OrgMembership.organization_id == current_user.organization_id,
        OrgMembership.is_active.is_(True),
    )
    result = await db.execute(stmt)
    membership = result.scalar_one_or_none()
    if not membership or membership.role not in (ROLE_SUPER_ADMIN, ROLE_ADMIN, ROLE_SECURITY_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to access this resource."
        )


class AdminController:
    # ═══════════════════════════════════════════════════════════════
    # MAIN DASHBOARD — complete end-to-end tracking
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    async def get_dashboard_summary(db: AsyncSession, current_user: User) -> dict[str, Any]:
        """Aggregate comprehensive end-to-end dashboard tracking data."""
        await _verify_admin(db, current_user)

        today = utc_now().date()
        seven_days_ago = today - timedelta(days=7)
        thirty_days_ago = today - timedelta(days=30)

        # ═══════════════════════════════════════════════════════
        # 1. PLATFORM OVERVIEW — complete counts
        # ═══════════════════════════════════════════════════════
        total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
        active_users = (await db.execute(select(func.count(User.id)).where(User.is_active.is_(True)))).scalar() or 0
        total_orgs = (await db.execute(select(func.count(Organization.id)))).scalar() or 0

        total_conversations = (
            await db.execute(select(func.count(Conversation.id)).where(Conversation.deleted_at.is_(None)))
        ).scalar() or 0

        total_messages = (
            await db.execute(select(func.count(Message.id)).where(Message.deleted_at.is_(None)))
        ).scalar() or 0

        total_tokens = int(
            (await db.execute(select(func.coalesce(func.sum(UsageEvent.total_tokens), 0)))).scalar() or 0
        )
        total_cost = float(
            (await db.execute(select(func.coalesce(func.sum(UsageEvent.cost_usd), 0)))).scalar() or 0
        )
        total_requests = int(
            (await db.execute(select(func.count(UsageEvent.id)))).scalar() or 0
        )

        # ═══════════════════════════════════════════════════════
        # 2. TODAY'S ACTIVITY
        # ═══════════════════════════════════════════════════════
        today_conversations = (
            await db.execute(
                select(func.count(Conversation.id))
                .where(Conversation.deleted_at.is_(None), func.date(Conversation.created_at) == today)
            )
        ).scalar() or 0

        today_messages = (
            await db.execute(
                select(func.count(Message.id))
                .where(Message.deleted_at.is_(None), func.date(Message.created_at) == today)
            )
        ).scalar() or 0

        today_tokens = int(
            (await db.execute(
                select(func.coalesce(func.sum(UsageEvent.total_tokens), 0))
                .where(func.date(UsageEvent.created_at) == today)
            )).scalar() or 0
        )

        today_new_users = (
            await db.execute(
                select(func.count(User.id)).where(func.date(User.created_at) == today)
            )
        ).scalar() or 0

        today_errors = int(
            (await db.execute(
                select(func.count(UsageEvent.id))
                .where(func.date(UsageEvent.created_at) == today, UsageEvent.status != "success")
            )).scalar() or 0
        )

        # ═══════════════════════════════════════════════════════
        # 3. GROWTH METRICS (30 days)
        # ═══════════════════════════════════════════════════════
        growth_rows = (
            await db.execute(
                select(
                    func.date(User.created_at).label("day"),
                    func.count(User.id).label("count"),
                )
                .where(func.date(User.created_at) >= thirty_days_ago)
                .group_by(func.date(User.created_at))
                .order_by(func.date(User.created_at))
            )
        ).all()

        signup_growth = [
            {"date": str(row.day), "count": int(row.count)}
            for row in growth_rows
        ]

        conv_rows = (
            await db.execute(
                select(
                    func.date(Conversation.created_at).label("day"),
                    func.count(Conversation.id).label("count"),
                )
                .where(
                    func.date(Conversation.created_at) >= thirty_days_ago,
                    Conversation.deleted_at.is_(None),
                )
                .group_by(func.date(Conversation.created_at))
                .order_by(func.date(Conversation.created_at))
            )
        ).all()

        conversation_growth = [
            {"date": str(row.day), "count": int(row.count)}
            for row in conv_rows
        ]

        # ═══════════════════════════════════════════════════════
        # 4. USAGE OVER TIME (last 7 days)
        # ═══════════════════════════════════════════════════════
        recent_usage_rows = (
            await db.execute(
                select(
                    func.date(UsageEvent.created_at).label("day"),
                    func.sum(UsageEvent.total_tokens).label("tokens"),
                    func.sum(UsageEvent.cost_usd).label("cost"),
                    func.count(UsageEvent.id).label("requests"),
                    func.avg(UsageEvent.latency_ms).label("avg_latency"),
                )
                .where(func.date(UsageEvent.created_at) >= seven_days_ago)
                .group_by(func.date(UsageEvent.created_at))
                .order_by(func.date(UsageEvent.created_at))
            )
        ).all()

        usage_over_time = [
            {
                "date": str(row.day),
                "tokens": int(row.tokens or 0),
                "cost": float(row.cost or 0),
                "requests": int(row.requests or 0),
                "avg_latency_ms": round(float(row.avg_latency or 0), 1),
            }
            for row in recent_usage_rows
        ]

        # ═══════════════════════════════════════════════════════
        # 5. MODEL BREAKDOWN
        # ═══════════════════════════════════════════════════════
        model_rows = (
            await db.execute(
                select(
                    UsageEvent.provider_name,
                    UsageEvent.model_name,
                    func.sum(UsageEvent.total_tokens).label("tokens"),
                    func.sum(UsageEvent.cost_usd).label("cost"),
                    func.count(UsageEvent.id).label("requests"),
                    func.avg(UsageEvent.latency_ms).label("avg_latency"),
                )
                .group_by(UsageEvent.provider_name, UsageEvent.model_name)
                .order_by(desc(func.sum(UsageEvent.cost_usd)))
            )
        ).all()

        model_breakdown = [
            {
                "provider": row.provider_name,
                "model": row.model_name,
                "tokens": int(row.tokens or 0),
                "cost": float(row.cost or 0),
                "requests": int(row.requests or 0),
                "avg_latency_ms": round(float(row.avg_latency or 0), 1),
            }
            for row in model_rows
        ]

        # ═══════════════════════════════════════════════════════
        # 6. PROVIDER BREAKDOWN
        # ═══════════════════════════════════════════════════════
        provider_rows = (
            await db.execute(
                select(
                    UsageEvent.provider_name,
                    func.sum(UsageEvent.total_tokens).label("tokens"),
                    func.sum(UsageEvent.cost_usd).label("cost"),
                    func.count(UsageEvent.id).label("requests"),
                )
                .group_by(UsageEvent.provider_name)
            )
        ).all()

        provider_breakdown = [
            {
                "provider": row.provider_name,
                "tokens": int(row.tokens or 0),
                "cost": float(row.cost or 0),
                "requests": int(row.requests or 0),
            }
            for row in provider_rows
        ]

        # ═══════════════════════════════════════════════════════
        # 7. ALL USERS (paginated, up to 200)
        # ═══════════════════════════════════════════════════════
        users_query = (
            await db.execute(
                select(User, OrgMembership.role)
                .outerjoin(OrgMembership, (OrgMembership.user_id == User.id) & OrgMembership.is_active.is_(True))
                .order_by(User.created_at.desc())
                .limit(200)
            )
        )
        users_rows = users_query.all()

        # Batch-fetch aggregate data for all users at once
        if users_rows:
            user_ids = [u.id for u, _ in users_rows]

            # Conversation counts per user
            conv_counts_raw = (
                await db.execute(
                    select(Conversation.user_id, func.count(Conversation.id).label("cnt"))
                    .where(Conversation.user_id.in_(user_ids), Conversation.deleted_at.is_(None))
                    .group_by(Conversation.user_id)
                )
            ).all()
            conv_counts = {str(r.user_id): int(r.cnt) for r in conv_counts_raw}

            # Message counts per user
            msg_counts_raw = (
                await db.execute(
                    select(Conversation.user_id, func.count(Message.id).label("cnt"))
                    .join(Message, Message.conversation_id == Conversation.id)
                    .where(
                        Conversation.user_id.in_(user_ids),
                        Conversation.deleted_at.is_(None),
                        Message.deleted_at.is_(None),
                    )
                    .group_by(Conversation.user_id)
                )
            ).all()
            msg_counts = {str(r.user_id): int(r.cnt) for r in msg_counts_raw}

            # Token usage per user
            token_counts_raw = (
                await db.execute(
                    select(UsageEvent.user_id, func.coalesce(func.sum(UsageEvent.total_tokens), 0).label("tokens"))
                    .where(UsageEvent.user_id.in_(user_ids))
                    .group_by(UsageEvent.user_id)
                )
            ).all()
            token_counts = {str(r.user_id): int(r.tokens) for r in token_counts_raw}

            # Cost per user
            cost_raw = (
                await db.execute(
                    select(UsageEvent.user_id, func.coalesce(func.sum(UsageEvent.cost_usd), 0).label("cost"))
                    .where(UsageEvent.user_id.in_(user_ids))
                    .group_by(UsageEvent.user_id)
                )
            ).all()
            cost_map = {str(r.user_id): float(r.cost) for r in cost_raw}

            # Last active per user
            last_active_raw = (
                await db.execute(
                    select(Conversation.user_id, func.max(Message.created_at).label("last_active"))
                    .join(Message, Message.conversation_id == Conversation.id)
                    .where(
                        Conversation.user_id.in_(user_ids),
                        Conversation.deleted_at.is_(None),
                        Message.deleted_at.is_(None),
                    )
                    .group_by(Conversation.user_id)
                )
            ).all()
            last_active_map = {str(r.user_id): r.last_active for r in last_active_raw}
        else:
            conv_counts = {}
            msg_counts = {}
            token_counts = {}
            cost_map = {}
            last_active_map = {}

        users_list: list[dict[str, Any]] = []
        for user, role in users_rows:
            uid = str(user.id)
            users_list.append({
                "id": uid,
                "email": user.email,
                "role": role,
                "is_active": user.is_active,
                "created_at": _serialize(user.created_at),
                "conversation_count": conv_counts.get(uid, 0),
                "message_count": msg_counts.get(uid, 0),
                "total_tokens": token_counts.get(uid, 0),
                "total_cost": cost_map.get(uid, 0),
                "last_active": _serialize(last_active_map.get(uid)) if last_active_map.get(uid) else None,
            })

        # ═══════════════════════════════════════════════════════
        # 8. RECENT AUDIT LOGS (last 30)
        # ═══════════════════════════════════════════════════════
        recent_audit_rows = (
            await db.execute(
                select(AuditLog).order_by(AuditLog.created_at.desc()).limit(30)
            )
        ).scalars().all()

        recent_audit = [
            {
                "id": _serialize(log.id),
                "user_id": _serialize(log.user_id) if log.user_id else None,
                "event_type": log.event_type,
                "status": log.status,
                "provider_name": log.provider_name,
                "model_name": log.model_name,
                "input_tokens": log.input_tokens,
                "output_tokens": log.output_tokens,
                "latency_ms": log.latency_ms,
                "created_at": _serialize(log.created_at),
            }
            for log in recent_audit_rows
        ]

        # ═══════════════════════════════════════════════════════
        # 9. RECENT SECURITY EVENTS (last 30)
        # ═══════════════════════════════════════════════════════
        recent_security_rows = (
            await db.execute(
                select(SecurityEvent).order_by(SecurityEvent.created_at.desc()).limit(30)
            )
        ).scalars().all()

        recent_security = [
            {
                "id": _serialize(event.id),
                "user_id": _serialize(event.user_id) if event.user_id else None,
                "event_type": event.event_type,
                "severity": event.severity,
                "status": event.status,
                "ip_address": event.ip_address,
                "created_at": _serialize(event.created_at),
            }
            for event in recent_security_rows
        ]

        # ═══════════════════════════════════════════════════════
        # 10. DLP EVENTS (last 30)
        # ═══════════════════════════════════════════════════════
        recent_dlp_rows = (
            await db.execute(
                select(DlpEvent).order_by(DlpEvent.created_at.desc()).limit(30)
            )
        ).scalars().all()

        recent_dlp = [
            {
                "id": _serialize(event.id),
                "user_id": _serialize(event.user_id) if event.user_id else None,
                "action": event.action,
                "match_count": event.match_count,
                "redacted_excerpt": event.redacted_excerpt[:200] if event.redacted_excerpt else None,
                "created_at": _serialize(event.created_at),
            }
            for event in recent_dlp_rows
        ]

        # DLP summary stats
        dlp_total = (await db.execute(select(func.count(DlpEvent.id)))).scalar() or 0
        dlp_blocked = (
            await db.execute(
                select(func.count(DlpEvent.id)).where(DlpEvent.action == "block")
            )
        ).scalar() or 0

        # ═══════════════════════════════════════════════════════
        # 11. AUTH EVENTS SUMMARY
        # ═══════════════════════════════════════════════════════
        recent_signups = (
            await db.execute(
                select(func.count(User.id)).where(func.date(User.created_at) >= seven_days_ago)
            )
        ).scalar() or 0

        failed_logins = (
            await db.execute(
                select(func.count(SecurityEvent.id))
                .where(
                    SecurityEvent.event_type == "auth_failed_login",
                    func.date(SecurityEvent.created_at) >= seven_days_ago,
                )
            )
        ).scalar() or 0

        auth_events = {
            "recent_signups_7d": recent_signups,
            "failed_logins_7d": failed_logins,
            "total_users": total_users,
            "active_users": active_users,
        }

        # ═══════════════════════════════════════════════════════
        # 12. SYSTEM HEALTH
        # ═══════════════════════════════════════════════════════
        db_healthy_result = await db.execute(text("SELECT 1"))
        db_healthy = db_healthy_result.scalar() == 1

        system_health = {
            "database": "healthy" if db_healthy else "degraded",
            "total_organizations": total_orgs,
            "total_requests": total_requests,
        }

        # ═══════════════════════════════════════════════════════
        # 13. ERROR / FAILURE STATS
        # ═══════════════════════════════════════════════════════
        failed_requests = int(
            (await db.execute(
                select(func.count(UsageEvent.id)).where(UsageEvent.status != "success")
            )).scalar() or 0
        )

        # ═══════════════════════════════════════════════════════
        # ASSEMBLE RESPONSE
        # ═══════════════════════════════════════════════════════
        return {
            "overview": {
                "total_users": total_users,
                "active_users": active_users,
                "total_conversations": total_conversations,
                "total_messages": total_messages,
                "total_tokens": total_tokens,
                "total_cost": total_cost,
                "total_requests": total_requests,
                "total_organizations": total_orgs,
                "failed_requests": failed_requests,
            },
            "today": {
                "conversations": today_conversations,
                "messages": today_messages,
                "tokens": today_tokens,
                "new_users": today_new_users,
                "errors": today_errors,
            },
            "auth": auth_events,
            "health": system_health,
            "growth": {
                "signups_30d": signup_growth,
                "conversations_30d": conversation_growth,
            },
            "users": users_list,
            "usage_over_time": usage_over_time,
            "model_breakdown": model_breakdown,
            "provider_breakdown": provider_breakdown,
            "recent_audit": recent_audit,
            "recent_security": recent_security,
            "dlp": {
                "events": recent_dlp,
                "total": dlp_total,
                "blocked": dlp_blocked,
            },
        }

    # ═══════════════════════════════════════════════════════════════
    # USER DETAIL — complete per-user tracking
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    async def get_user_detail(
        db: AsyncSession,
        current_user: User,
        target_user_id: uuid.UUID,
        page: int = 1,
        per_page: int = 20,
    ) -> dict[str, Any]:
        """Get complete end-to-end tracking data for a specific user."""
        await _verify_admin(db, current_user)

        # Get user and membership
        user = await db.get(User, target_user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

        membership = None
        if user.organization_id:
            membership = await db.execute(
                select(OrgMembership).where(
                    OrgMembership.user_id == user.id,
                    OrgMembership.organization_id == user.organization_id,
                    OrgMembership.is_active.is_(True),
                )
            )
            membership = membership.scalar_one_or_none()

        # Conversations (paginated)
        offset = (page - 1) * per_page
        conv_total = (
            await db.execute(
                select(func.count(Conversation.id))
                .where(Conversation.user_id == user.id, Conversation.deleted_at.is_(None))
            )
        ).scalar() or 0

        conv_rows = (
            await db.execute(
                select(Conversation)
                .where(Conversation.user_id == user.id, Conversation.deleted_at.is_(None))
                .order_by(Conversation.updated_at.desc())
                .offset(offset)
                .limit(per_page)
            )
        ).scalars().all()

        conversations_list = []
        for conv in conv_rows:
            msg_count = (
                await db.execute(
                    select(func.count(Message.id))
                    .where(Message.conversation_id == conv.id, Message.deleted_at.is_(None))
                )
            ).scalar() or 0

            conversations_list.append({
                "id": _serialize(conv.id),
                "title": conv.title,
                "created_at": _serialize(conv.created_at),
                "updated_at": _serialize(conv.updated_at),
                "message_count": msg_count,
            })

        # Usage stats
        user_tokens = int(
            (await db.execute(
                select(func.coalesce(func.sum(UsageEvent.total_tokens), 0))
                .where(UsageEvent.user_id == user.id)
            )).scalar() or 0
        )
        user_cost = float(
            (await db.execute(
                select(func.coalesce(func.sum(UsageEvent.cost_usd), 0))
                .where(UsageEvent.user_id == user.id)
            )).scalar() or 0
        )
        user_requests = int(
            (await db.execute(
                select(func.count(UsageEvent.id)).where(UsageEvent.user_id == user.id)
            )).scalar() or 0
        )

        # Recent usage (last 7 days)
        today = utc_now().date()
        seven_days_ago = today - timedelta(days=7)
        recent_usage = (
            await db.execute(
                select(
                    func.date(UsageEvent.created_at).label("day"),
                    func.sum(UsageEvent.total_tokens).label("tokens"),
                    func.sum(UsageEvent.cost_usd).label("cost"),
                    func.count(UsageEvent.id).label("requests"),
                )
                .where(
                    UsageEvent.user_id == user.id,
                    func.date(UsageEvent.created_at) >= seven_days_ago,
                )
                .group_by(func.date(UsageEvent.created_at))
                .order_by(func.date(UsageEvent.created_at))
            )
        ).all()

        usage_history = [
            {
                "date": str(row.day),
                "tokens": int(row.tokens or 0),
                "cost": float(row.cost or 0),
                "requests": int(row.requests or 0),
            }
            for row in recent_usage
        ]

        # Model breakdown for this user
        model_rows = (
            await db.execute(
                select(
                    UsageEvent.provider_name,
                    UsageEvent.model_name,
                    func.sum(UsageEvent.total_tokens).label("tokens"),
                    func.sum(UsageEvent.cost_usd).label("cost"),
                    func.count(UsageEvent.id).label("requests"),
                )
                .where(UsageEvent.user_id == user.id)
                .group_by(UsageEvent.provider_name, UsageEvent.model_name)
                .order_by(desc(func.sum(UsageEvent.cost_usd)))
            )
        ).all()

        model_usage = [
            {
                "provider": row.provider_name,
                "model": row.model_name,
                "tokens": int(row.tokens or 0),
                "cost": float(row.cost or 0),
                "requests": int(row.requests or 0),
            }
            for row in model_rows
        ]

        # Recent audit logs for this user
        audit_rows = (
            await db.execute(
                select(AuditLog)
                .where(AuditLog.user_id == user.id)
                .order_by(AuditLog.created_at.desc())
                .limit(20)
            )
        ).scalars().all()

        audit_logs = [
            {
                "id": _serialize(log.id),
                "event_type": log.event_type,
                "status": log.status,
                "provider_name": log.provider_name,
                "model_name": log.model_name,
                "input_tokens": log.input_tokens,
                "output_tokens": log.output_tokens,
                "latency_ms": log.latency_ms,
                "created_at": _serialize(log.created_at),
            }
            for log in audit_rows
        ]

        return {
            "user": {
                "id": _serialize(user.id),
                "email": user.email,
                "role": membership.role if membership else None,
                "is_active": user.is_active,
                "created_at": _serialize(user.created_at),
                "organization_id": _serialize(user.organization_id) if user.organization_id else None,
            },
            "stats": {
                "total_conversations": conv_total,
                "total_tokens": user_tokens,
                "total_cost": user_cost,
                "total_requests": user_requests,
            },
            "conversations": {
                "items": conversations_list,
                "total": conv_total,
                "page": page,
                "per_page": per_page,
                "total_pages": max(1, (conv_total + per_page - 1) // per_page),
            },
            "usage_history": usage_history,
            "model_usage": model_usage,
            "recent_audit": audit_logs,
        }

    # ═══════════════════════════════════════════════════════════════
    # PAGINATED AUDIT LOGS
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    async def list_audit_logs(
        db: AsyncSession,
        current_user: User,
        page: int = 1,
        per_page: int = 30,
        status: str | None = None,
        event_type: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """Paginated audit logs with filters."""
        await _verify_admin(db, current_user)

        offset = (page - 1) * per_page

        base_query = select(AuditLog)
        count_query = select(func.count(AuditLog.id))

        if status:
            base_query = base_query.where(AuditLog.status == status)
            count_query = count_query.where(AuditLog.status == status)
        if event_type:
            base_query = base_query.where(AuditLog.event_type == event_type)
            count_query = count_query.where(AuditLog.event_type == event_type)
        if start_date:
            base_query = base_query.where(func.date(AuditLog.created_at) >= start_date)
            count_query = count_query.where(func.date(AuditLog.created_at) >= start_date)
        if end_date:
            base_query = base_query.where(func.date(AuditLog.created_at) <= end_date)
            count_query = count_query.where(func.date(AuditLog.created_at) <= end_date)

        total = (await db.execute(count_query)).scalar() or 0

        rows = (
            await db.execute(
                base_query
                .order_by(AuditLog.created_at.desc())
                .offset(offset)
                .limit(per_page)
            )
        ).scalars().all()

        # Get distinct event types for filter dropdown
        event_types_result = await db.execute(
            select(AuditLog.event_type).distinct().order_by(AuditLog.event_type)
        )
        event_types = [r[0] for r in event_types_result.all()]

        items = [
            {
                "id": _serialize(log.id),
                "user_id": _serialize(log.user_id) if log.user_id else None,
                "event_type": log.event_type,
                "status": log.status,
                "provider_name": log.provider_name,
                "model_name": log.model_name,
                "input_tokens": log.input_tokens,
                "output_tokens": log.output_tokens,
                "latency_ms": log.latency_ms,
                "created_at": _serialize(log.created_at),
            }
            for log in rows
        ]

        return {
            "items": items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": max(1, (total + per_page - 1) // per_page),
            "event_types": event_types,
        }

    # ═══════════════════════════════════════════════════════════════
    # PAGINATED SECURITY EVENTS
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    async def list_security_events(
        db: AsyncSession,
        current_user: User,
        page: int = 1,
        per_page: int = 30,
        severity: str | None = None,
        status: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """Paginated security events with filters."""
        await _verify_admin(db, current_user)

        offset = (page - 1) * per_page

        base_query = select(SecurityEvent)
        count_query = select(func.count(SecurityEvent.id))

        if severity:
            base_query = base_query.where(SecurityEvent.severity == severity)
            count_query = count_query.where(SecurityEvent.severity == severity)
        if status:
            base_query = base_query.where(SecurityEvent.status == status)
            count_query = count_query.where(SecurityEvent.status == status)
        if start_date:
            base_query = base_query.where(func.date(SecurityEvent.created_at) >= start_date)
            count_query = count_query.where(func.date(SecurityEvent.created_at) >= start_date)
        if end_date:
            base_query = base_query.where(func.date(SecurityEvent.created_at) <= end_date)
            count_query = count_query.where(func.date(SecurityEvent.created_at) <= end_date)

        total = (await db.execute(count_query)).scalar() or 0

        rows = (
            await db.execute(
                base_query
                .order_by(SecurityEvent.created_at.desc())
                .offset(offset)
                .limit(per_page)
            )
        ).scalars().all()

        # Severity distribution for chart
        severity_dist = (
            await db.execute(
                select(
                    SecurityEvent.severity,
                    func.count(SecurityEvent.id).label("count"),
                )
                .group_by(SecurityEvent.severity)
            )
        ).all()

        items = [
            {
                "id": _serialize(event.id),
                "user_id": _serialize(event.user_id) if event.user_id else None,
                "event_type": event.event_type,
                "severity": event.severity,
                "status": event.status,
                "ip_address": event.ip_address,
                "created_at": _serialize(event.created_at),
            }
            for event in rows
        ]

        return {
            "items": items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": max(1, (total + per_page - 1) // per_page),
            "severity_distribution": [
                {"severity": row.severity, "count": int(row.count)}
                for row in severity_dist
            ],
        }

    # ═══════════════════════════════════════════════════════════════
    # PAGINATED DLP EVENTS
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    async def list_dlp_events(
        db: AsyncSession,
        current_user: User,
        page: int = 1,
        per_page: int = 30,
        action: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """Paginated DLP events with filters."""
        await _verify_admin(db, current_user)

        offset = (page - 1) * per_page

        base_query = select(DlpEvent)
        count_query = select(func.count(DlpEvent.id))

        if action:
            base_query = base_query.where(DlpEvent.action == action)
            count_query = count_query.where(DlpEvent.action == action)
        if start_date:
            base_query = base_query.where(func.date(DlpEvent.created_at) >= start_date)
            count_query = count_query.where(func.date(DlpEvent.created_at) >= start_date)
        if end_date:
            base_query = base_query.where(func.date(DlpEvent.created_at) <= end_date)
            count_query = count_query.where(func.date(DlpEvent.created_at) <= end_date)

        total = (await db.execute(count_query)).scalar() or 0

        rows = (
            await db.execute(
                base_query
                .order_by(DlpEvent.created_at.desc())
                .offset(offset)
                .limit(per_page)
            )
        ).scalars().all()

        # Action distribution for chart
        action_dist = (
            await db.execute(
                select(
                    DlpEvent.action,
                    func.count(DlpEvent.id).label("count"),
                )
                .group_by(DlpEvent.action)
            )
        ).all()

        items = [
            {
                "id": _serialize(event.id),
                "user_id": _serialize(event.user_id) if event.user_id else None,
                "action": event.action,
                "match_count": event.match_count,
                "redacted_excerpt": event.redacted_excerpt[:200] if event.redacted_excerpt else None,
                "created_at": _serialize(event.created_at),
            }
            for event in rows
        ]

        return {
            "items": items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": max(1, (total + per_page - 1) // per_page),
            "action_distribution": [
                {"action": row.action, "count": int(row.count)}
                for row in action_dist
            ],
        }

    # ═══════════════════════════════════════════════════════════════
    # CONVERSATION DETAIL — view any conversation
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    async def get_conversation_detail(
        db: AsyncSession,
        current_user: User,
        conversation_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Get full conversation detail with messages (admin view, any user's conversation)."""
        await _verify_admin(db, current_user)

        conv = await db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.deleted_at.is_(None),
            )
        )
        conv = conv.scalar_one_or_none()
        if not conv:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")

        # Get user info
        user = await db.get(User, conv.user_id)

        # Get messages
        messages = (
            await db.execute(
                select(Message)
                .where(Message.conversation_id == conv.id, Message.deleted_at.is_(None))
                .order_by(Message.created_at.asc())
            )
        ).scalars().all()

        return {
            "conversation": {
                "id": _serialize(conv.id),
                "title": conv.title,
                "user_id": _serialize(conv.user_id),
                "user_email": user.email if user else None,
                "created_at": _serialize(conv.created_at),
                "updated_at": _serialize(conv.updated_at),
            },
            "messages": [
                {
                    "id": _serialize(msg.id),
                    "role": msg.role,
                    "content": msg.content[:2000] if msg.content else "",
                    "model_used": msg.model_used,
                    "provider_used": msg.provider_used,
                    "created_at": _serialize(msg.created_at),
                }
                for msg in messages
            ],
        }

    # ═══════════════════════════════════════════════════════════════
    # ALL CONVERSATIONS — system-wide view
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    async def list_all_conversations(
        db: AsyncSession,
        current_user: User,
        page: int = 1,
        per_page: int = 20,
        search: str | None = None,
    ) -> dict[str, Any]:
        """List all conversations across the system with user info."""
        await _verify_admin(db, current_user)

        offset = (page - 1) * per_page

        base_query = select(Conversation).where(Conversation.deleted_at.is_(None))
        count_query = select(func.count(Conversation.id)).where(Conversation.deleted_at.is_(None))

        if search:
            search_filter = Conversation.title.ilike(f"%{search}%")
            base_query = base_query.where(search_filter)
            count_query = count_query.where(search_filter)

        total = (await db.execute(count_query)).scalar() or 0

        conv_rows = (
            await db.execute(
                base_query
                .order_by(Conversation.updated_at.desc())
                .offset(offset)
                .limit(per_page)
            )
        ).scalars().all()

        items = []
        for conv in conv_rows:
            user = await db.get(User, conv.user_id)
            msg_count = (
                await db.execute(
                    select(func.count(Message.id))
                    .where(Message.conversation_id == conv.id, Message.deleted_at.is_(None))
                )
            ).scalar() or 0

            items.append({
                "id": _serialize(conv.id),
                "title": conv.title,
                "user_id": _serialize(conv.user_id),
                "user_email": user.email if user else "unknown",
                "created_at": _serialize(conv.created_at),
                "updated_at": _serialize(conv.updated_at),
                "message_count": msg_count,
            })

        return {
            "items": items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": max(1, (total + per_page - 1) // per_page),
        }
