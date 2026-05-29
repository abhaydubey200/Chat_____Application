import asyncio
from sqlalchemy import text
from app.core.database import Base, engine
from app.db.models import (
    User,
    Conversation,
    Message,
    Organization,
    OrgMembership,
    AuditLog,
    UsageEvent,
    DlpRule,
    DlpEvent,
    SecurityEvent,
    ProviderPolicy,
    ModelPolicy,
    RetentionPolicy,
    RetentionJob,
    UsageDailyAggregate,
)

async def init_models():
    async with engine.begin() as conn:
        print("Creating governance schema...")
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS governance"))
        print("Creating tables in PostgreSQL...")
        # For development/V1, create all tables if they do not exist
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables initialized successfully.")

if __name__ == "__main__":
    asyncio.run(init_models())
