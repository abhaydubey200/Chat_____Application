"""Add full-text search GIN index on conversations.title (trigram similarity search).

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Enable pg_trgm extension and add GIN trigram index on conversations.title."""
    # Enable pg_trgm extension for trigram similarity search
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # Create GIN index using trigram operator class for fast ILIKE / similarity searches
    op.create_index(
        "ix_conversations_title_fts",
        "conversations",
        ["title"],
        postgresql_using="gin",
        postgresql_ops={"title": "gin_trgm_ops"},
    )


def downgrade() -> None:
    """Drop the GIN index."""
    op.drop_index("ix_conversations_title_fts", table_name="conversations")
