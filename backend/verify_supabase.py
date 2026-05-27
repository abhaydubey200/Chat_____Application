import asyncio
import sys
import os

from dotenv import load_dotenv

# Load .env file relative to the script directory to ensure environment variables are present
dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(dotenv_path)

# Add current directory to path to resolve app package
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import verify_database_connection, close_db

async def main():
    print("Testing connection to database/Supabase...")
    try:
        success = await verify_database_connection()
        if success:
            print("Database connection successful!")
            sys.exit(0)
        else:
            print("Failed to connect to the database/Supabase.")
            sys.exit(1)
    finally:
        await close_db()

if __name__ == "__main__":
    asyncio.run(main())
