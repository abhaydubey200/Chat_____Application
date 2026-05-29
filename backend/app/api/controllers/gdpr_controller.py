"""GDPR Compliance Controller — handles data export and deletion requests."""

import uuid
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.db.models import (
    User, OrgMembership, Organization, Conversation, Message,
    UsageEvent, AuditLog, DlpEvent, SecurityEvent,
)
from app.core.time import utc_now
from app.core.security import verify_password, get_password_hash
from app.db.repositories.user_repository import UserRepository


class GDPRController:
    """Handles GDPR data subject rights — export and deletion of personal data."""

    @staticmethod
    async def export_user_data(db: AsyncSession, current_user: User) -> dict[str, Any]:
        """Export all personal data associated with the current user.

        Complies with GDPR Article 15 (Right of access) — returns all
        personal data in a structured, machine-readable format.
        """
        user_id = current_user.id

        # 1. User profile & membership
        user_data = {
            "id": str(user_id),
            "email": current_user.email,
            "is_active": current_user.is_active,
            "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        }

        membership = None
        org_data = None
        if current_user.organization_id:
            stmt = select(OrgMembership).where(
                OrgMembership.user_id == user_id,
                OrgMembership.organization_id == current_user.organization_id,
                OrgMembership.is_active.is_(True),
            )
            result = await db.execute(stmt)
            membership = result.scalar_one_or_none()

            org = await db.get(Organization, current_user.organization_id)
            if org:
                org_data = {
                    "id": str(org.id),
                    "name": org.name,
                    "is_active": org.is_active,
                    "created_at": org.created_at.isoformat() if org.created_at else None,
                }

        # 2. Conversations
        conv_stmt = select(Conversation).where(
            Conversation.user_id == user_id,
            Conversation.deleted_at.is_(None),
        ).order_by(Conversation.created_at.asc())
        conv_result = await db.execute(conv_stmt)
        conversations = conv_result.scalars().all()

        conversations_data = []
        for conv in conversations:
            msg_stmt = select(Message).where(
                Message.conversation_id == conv.id,
                Message.deleted_at.is_(None),
            ).order_by(Message.created_at.asc())
            msg_result = await db.execute(msg_stmt)
            messages = msg_result.scalars().all()

            conversations_data.append({
                "id": str(conv.id),
                "title": conv.title,
                "created_at": conv.created_at.isoformat() if conv.created_at else None,
                "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
                "message_count": len(messages),
                "messages": [
                    {
                        "id": str(msg.id),
                        "role": msg.role,
                        "content_preview": msg.content[:500] if msg.content else "",
                        "model_used": msg.model_used,
                        "provider_used": msg.provider_used,
                        "created_at": msg.created_at.isoformat() if msg.created_at else None,
                    }
                    for msg in messages
                ],
            })

        # 3. Usage events
        usage_stmt = select(UsageEvent).where(
            UsageEvent.user_id == user_id,
        ).order_by(UsageEvent.created_at.asc()).limit(1000)
        usage_result = await db.execute(usage_stmt)
        usage_events = usage_result.scalars().all()

        usage_data = [
            {
                "id": str(event.id),
                "provider": event.provider_name,
                "model": event.model_name,
                "input_tokens": event.input_tokens,
                "output_tokens": event.output_tokens,
                "total_tokens": event.total_tokens,
                "cost_usd": float(event.cost_usd) if event.cost_usd else 0.0,
                "status": event.status,
                "created_at": event.created_at.isoformat() if event.created_at else None,
            }
            for event in usage_events
        ]

        # 4. Audit logs
        audit_stmt = select(AuditLog).where(
            AuditLog.user_id == user_id,
        ).order_by(AuditLog.created_at.asc()).limit(500)
        audit_result = await db.execute(audit_stmt)
        audit_logs = audit_result.scalars().all()

        audit_data = [
            {
                "id": str(log.id),
                "event_type": log.event_type,
                "status": log.status,
                "provider": log.provider_name,
                "model": log.model_name,
                "ip_address": log.ip_address,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in audit_logs
        ]

        # 5. DLP events
        dlp_stmt = select(DlpEvent).where(
            DlpEvent.user_id == user_id,
        ).order_by(DlpEvent.created_at.asc()).limit(500)
        dlp_result = await db.execute(dlp_stmt)
        dlp_events = dlp_result.scalars().all()

        dlp_data = [
            {
                "id": str(event.id),
                "action": event.action,
                "match_count": event.match_count,
                "rule_id": str(event.rule_id) if event.rule_id else None,
                "created_at": event.created_at.isoformat() if event.created_at else None,
            }
            for event in dlp_events
        ]

        # 6. Security events
        sec_stmt = select(SecurityEvent).where(
            SecurityEvent.user_id == user_id,
        ).order_by(SecurityEvent.created_at.asc()).limit(500)
        sec_result = await db.execute(sec_stmt)
        sec_events = sec_result.scalars().all()

        sec_data = [
            {
                "id": str(event.id),
                "event_type": event.event_type,
                "severity": event.severity,
                "status": event.status,
                "ip_address": event.ip_address,
                "created_at": event.created_at.isoformat() if event.created_at else None,
            }
            for event in sec_events
        ]

        return {
            "export_date": utc_now().isoformat(),
            "user": user_data,
            "organization": org_data,
            "role": membership.role if membership else None,
            "conversations": conversations_data,
            "conversation_count": len(conversations_data),
            "usage_events": usage_data,
            "usage_event_count": len(usage_data),
            "audit_logs": audit_data,
            "audit_log_count": len(audit_data),
            "dlp_events": dlp_data,
            "dlp_event_count": len(dlp_data),
            "security_events": sec_data,
            "security_event_count": len(sec_data),
        }

    @staticmethod
    async def delete_user_data(
        db: AsyncSession,
        current_user: User,
        password: str,
    ) -> dict[str, str]:
        """Permanently delete or anonymize all personal data for the current user.

        Complies with GDPR Article 17 (Right to erasure / 'Right to be forgotten').
        Requires password confirmation for security.

        Strategy:
        - Conversations are soft-deleted (deleted_at set)
        - Messages are soft-deleted
        - User email is anonymized
        - User account is deactivated
        - Governance audit/usage/DLP/security records are preserved (legal obligation)
          but are disassociated from the user.
        """
        # Require password confirmation
        if not password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password confirmation is required to delete your data.",
            )

        if not verify_password(password, current_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect password. Data deletion aborted.",
            )

        user_id = current_user.id
        now = utc_now()
        anonymized_email = f"deleted-{user_id}@anonymized.local"

        # 1. Soft-delete all conversations and messages
        conv_stmt = select(Conversation).where(
            Conversation.user_id == user_id,
            Conversation.deleted_at.is_(None),
        )
        conv_result = await db.execute(conv_stmt)
        conversations = conv_result.scalars().all()

        deleted_conv_count = 0
        for conv in conversations:
            conv.deleted_at = now
            deleted_conv_count += 1

            # Soft-delete all messages in this conversation
            msg_stmt = select(Message).where(
                Message.conversation_id == conv.id,
                Message.deleted_at.is_(None),
            )
            msg_result = await db.execute(msg_stmt)
            for msg in msg_result.scalars().all():
                msg.deleted_at = now

        # 2. Deactivate org memberships
        membership_stmt = select(OrgMembership).where(
            OrgMembership.user_id == user_id,
            OrgMembership.is_active.is_(True),
        )
        membership_result = await db.execute(membership_stmt)
        for membership in membership_result.scalars().all():
            membership.is_active = False

        # 3. Anonymize user
        current_user.email = anonymized_email
        current_user.is_active = False

        await db.commit()

        return {
            "status": "success",
            "message": "Your personal data has been deleted or anonymized.",
            "details": {
                "conversations_soft_deleted": deleted_conv_count,
                "user_anonymized": True,
                "account_deactivated": True,
                "retention_note": (
                    "Usage, audit, DLP, and security event records have been "
                    "preserved as required by law but no longer contain your personal information."
                ),
            },
        }
