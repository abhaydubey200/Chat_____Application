"""Initial baseline migration — creates all tables matching the current ORM models.

Revision ID: 0001
Revises: None
Create Date: 2026-05-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables and governance schema."""

    # Create governance schema
    op.execute("CREATE SCHEMA IF NOT EXISTS governance")

    # ── Public schema tables ──────────────────────────────────────────────

    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_organization_id", "users", ["organization_id"])

    op.create_table(
        "org_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_org_memberships_org_id", "org_memberships", ["organization_id"])
    op.create_index("ix_org_memberships_user_id", "org_memberships", ["user_id"])
    op.create_index("ix_org_memberships_role", "org_memberships", ["role"])
    op.create_unique_constraint("uq_org_memberships_org_user", "org_memberships", ["organization_id", "user_id"])

    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(), nullable=False, server_default=sa.text("'New Conversation'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])
    op.create_index("ix_conversations_organization_id", "conversations", ["organization_id"])

    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("content", sa.String(), nullable=False),
        sa.Column("model_used", sa.String(), nullable=True),
        sa.Column("provider_used", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])

    # ── Governance schema tables ──────────────────────────────────────────

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("request_id", sa.String(64), index=True, nullable=True),
        sa.Column("session_id", sa.String(64), index=True, nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), index=True, nullable=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), index=True, nullable=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), index=True, nullable=True),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'success'")),
        sa.Column("provider_name", sa.String(80), nullable=True),
        sa.Column("model_name", sa.String(120), nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(256), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="governance",
    )
    op.create_index("ix_audit_logs_user_id_created_at", "audit_logs", ["user_id", "created_at"], schema="governance")
    op.create_index("ix_audit_logs_request_id", "audit_logs", ["request_id"], schema="governance")
    op.create_index("ix_audit_logs_event_type", "audit_logs", ["event_type"], schema="governance")

    op.create_table(
        "usage_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("request_id", sa.String(64), index=True, nullable=True),
        sa.Column("session_id", sa.String(64), index=True, nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), index=True, nullable=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), index=True, nullable=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), index=True, nullable=True),
        sa.Column("provider_name", sa.String(80), nullable=False),
        sa.Column("model_name", sa.String(120), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("cost_usd", sa.Numeric(12, 6), nullable=False, server_default=sa.text("0")),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("stream_duration_ms", sa.Integer(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'success'")),
        sa.Column("metadata", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="governance",
    )
    op.create_index("ix_usage_events_user_id_created_at", "usage_events", ["user_id", "created_at"], schema="governance")
    op.create_index("ix_usage_events_provider", "usage_events", ["provider_name"], schema="governance")
    op.create_index("ix_usage_events_request_id", "usage_events", ["request_id"], schema="governance")

    op.create_table(
        "dlp_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("rule_type", sa.String(40), nullable=False),
        sa.Column("pattern", sa.Text(), nullable=False),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default=sa.text("'medium'")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="governance",
    )
    op.create_index("ix_dlp_rules_active", "dlp_rules", ["is_active"], schema="governance")

    op.create_table(
        "dlp_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("request_id", sa.String(64), index=True, nullable=True),
        sa.Column("session_id", sa.String(64), index=True, nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), index=True, nullable=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), index=True, nullable=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), index=True, nullable=True),
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("match_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("redacted_excerpt", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="governance",
    )
    op.create_index("ix_dlp_events_user_id_created_at", "dlp_events", ["user_id", "created_at"], schema="governance")
    op.create_index("ix_dlp_events_action", "dlp_events", ["action"], schema="governance")

    op.create_table(
        "security_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("request_id", sa.String(64), index=True, nullable=True),
        sa.Column("session_id", sa.String(64), index=True, nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), index=True, nullable=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), index=True, nullable=True),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default=sa.text("'medium'")),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'open'")),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(256), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="governance",
    )
    op.create_index("ix_security_events_user_id_created_at", "security_events", ["user_id", "created_at"], schema="governance")
    op.create_index("ix_security_events_event_type", "security_events", ["event_type"], schema="governance")

    op.create_table(
        "provider_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), index=True, nullable=False),
        sa.Column("provider_name", sa.String(80), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("allow_reasoning", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("max_cost_usd_per_day", sa.Numeric(12, 6), nullable=True),
        sa.Column("max_cost_usd_per_request", sa.Numeric(12, 6), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="governance",
    )
    op.create_index("ix_provider_policies_org_provider", "provider_policies",
                    ["organization_id", "provider_name"], schema="governance")

    op.create_table(
        "model_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), index=True, nullable=False),
        sa.Column("provider_name", sa.String(80), nullable=False),
        sa.Column("model_name", sa.String(120), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("cost_per_1k_input", sa.Numeric(12, 6), nullable=False, server_default=sa.text("0")),
        sa.Column("cost_per_1k_output", sa.Numeric(12, 6), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="governance",
    )
    op.create_index("ix_model_policies_org_provider_model", "model_policies",
                    ["organization_id", "provider_name", "model_name"], schema="governance")

    op.create_table(
        "retention_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), index=True, nullable=False),
        sa.Column("data_type", sa.String(60), nullable=False),
        sa.Column("soft_delete_after_days", sa.Integer(), nullable=True),
        sa.Column("hard_delete_after_days", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="governance",
    )
    op.create_index("ix_retention_policies_org_type", "retention_policies",
                    ["organization_id", "data_type"], schema="governance")

    op.create_table(
        "retention_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), index=True, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'running'")),
        sa.Column("records_affected", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("metadata", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb")),
        schema="governance",
    )
    op.create_index("ix_retention_jobs_org_started", "retention_jobs",
                    ["organization_id", "started_at"], schema="governance")

    op.create_table(
        "usage_daily_aggregates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), index=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), index=True, nullable=True),
        sa.Column("usage_date", sa.Date(), nullable=False),
        sa.Column("provider_name", sa.String(80), nullable=False),
        sa.Column("model_name", sa.String(120), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("cost_usd", sa.Numeric(12, 6), nullable=False, server_default=sa.text("0")),
        sa.Column("request_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="governance",
    )
    op.create_unique_constraint("uq_usage_daily", "usage_daily_aggregates",
                                ["organization_id", "user_id", "usage_date", "provider_name", "model_name"],
                                schema="governance")
    op.create_index("ix_usage_daily_org_date", "usage_daily_aggregates",
                    ["organization_id", "usage_date"], schema="governance")


def downgrade() -> None:
    """Drop all tables in reverse order of dependencies."""
    op.drop_table("usage_daily_aggregates", schema="governance")
    op.drop_table("retention_jobs", schema="governance")
    op.drop_table("retention_policies", schema="governance")
    op.drop_table("model_policies", schema="governance")
    op.drop_table("provider_policies", schema="governance")
    op.drop_table("security_events", schema="governance")
    op.drop_table("dlp_events", schema="governance")
    op.drop_table("dlp_rules", schema="governance")
    op.drop_table("usage_events", schema="governance")
    op.drop_table("audit_logs", schema="governance")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("org_memberships")
    op.drop_table("users")
    op.drop_table("organizations")
    op.execute("DROP SCHEMA IF EXISTS governance CASCADE")
