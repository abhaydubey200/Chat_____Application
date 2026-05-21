import asyncio
from app.core.database import Base, engine
from app.db.models import User, Conversation, Message  # Ensure models are imported for metadata registration

async def init_models():
    async with engine.begin() as conn:
        print("Creating tables in PostgreSQL...")
        # For development/V1, create all tables if they do not exist
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables initialized successfully.")

if __name__ == "__main__":
    asyncio.run(init_models())
