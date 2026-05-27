from typing import AsyncGenerator
import logging
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from app.core.config import settings
from app.core.db_url import build_connect_args

logger = logging.getLogger(__name__)

# Create async engine with production-grade pool configurations
# pool_size: base number of connections to keep open
# max_overflow: additional temporary connections allowed when pool is full
# pool_pre_ping: verify connection is alive before using (handles stale connections)
# pool_recycle: recycle connections after 3600 seconds to avoid timeout issues
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # Set to True for SQL debug logs in development
    pool_size=20,  # Increased from 10 for concurrent load
    max_overflow=40,  # Allow burst capacity
    pool_pre_ping=True,  # Health check before using connection
    pool_recycle=3600,  # Recycle connections after 1 hour
    connect_args=build_connect_args(
        settings.DATABASE_URL,
        {
            "timeout": 10,  # Connection timeout
            "command_timeout": 30,  # Command timeout
            "server_settings": {
                "application_name": settings.PROJECT_NAME,
                "jit": "off"  # Disable query JIT for predictability
            },
        },
        disable_ssl_verify=settings.SUPABASE_SSL_NO_VERIFY,
    ),
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Don't expire objects after commit
    autocommit=False,  # Require explicit commits
    autoflush=False,  # Explicit flush calls only
)

class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all ORM models."""
    pass

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to retrieve database session with automatic cleanup.
    
    Yields:
        AsyncSession: Active database session
        
    Raises:
        Exception: If transaction fails (automatically rollbacks)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database transaction failed: {e}", exc_info=True)
            raise
        finally:
            await session.close()

async def verify_database_connection() -> bool:
    """Verify database is accessible and responsive.
    
    Returns:
        bool: True if database is healthy, False otherwise
    """
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            return result.scalar() == 1
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False

async def init_db() -> None:
    """Initialize database schema (create tables if they don't exist).
    
    This should be called during application startup.
    """
    async with engine.begin() as conn:
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS governance"))
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("""
        CREATE OR REPLACE FUNCTION governance.prevent_update_delete()
        RETURNS trigger AS $$
        BEGIN
            IF TG_OP = 'DELETE' AND current_setting('governance.allow_delete', true) = 'true' THEN
                RETURN OLD;
            END IF;
            RAISE EXCEPTION 'Immutable governance table: updates/deletes are not allowed';
        END;
        $$ LANGUAGE plpgsql;
        """))
        await conn.execute(text("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'audit_logs_immutable') THEN
                CREATE TRIGGER audit_logs_immutable
                BEFORE UPDATE OR DELETE ON governance.audit_logs
                FOR EACH ROW EXECUTE FUNCTION governance.prevent_update_delete();
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'usage_events_immutable') THEN
                CREATE TRIGGER usage_events_immutable
                BEFORE UPDATE OR DELETE ON governance.usage_events
                FOR EACH ROW EXECUTE FUNCTION governance.prevent_update_delete();
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'dlp_events_immutable') THEN
                CREATE TRIGGER dlp_events_immutable
                BEFORE UPDATE OR DELETE ON governance.dlp_events
                FOR EACH ROW EXECUTE FUNCTION governance.prevent_update_delete();
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'security_events_immutable') THEN
                CREATE TRIGGER security_events_immutable
                BEFORE UPDATE OR DELETE ON governance.security_events
                FOR EACH ROW EXECUTE FUNCTION governance.prevent_update_delete();
            END IF;
        END $$;
        """))
    logger.info("Database schema initialized")

async def close_db() -> None:
    """Close database connection pool.
    
    This should be called during application shutdown.
    """
    await engine.dispose()
    logger.info("Database connections closed")
